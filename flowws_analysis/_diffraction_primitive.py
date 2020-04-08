import itertools

import numpy as np
import plato
import plato.draw.vispy
from plato.draw.vispy.internal import GLPrimitive, GLShapeDecorator
from plato.draw.internal import Shape, ShapeAttribute, ShapeDecorator
import scipy as sp, scipy.ndimage
import vispy.gloo

DEFAULT_COLORMAP = plato.cmap.cubehelix(np.linspace(0, 1, 128), s=0, r=.5)

@ShapeDecorator
class DiffractionBase(Shape):
     _ATTRIBUTES = list(itertools.starmap(ShapeAttribute, [
        ('positions', np.float32, (0, 0, 0), 2, True,
        'Real-space coordinates for each particle'),
        ('box', np.float32, (1, 1, 1, 0, 0, 0), 1, False,
        'Box parameters to use for FFT scaling using the HOOMD schema (Lx, Ly, Lz, xy, xz, yz)'),
        ('size', np.uint32, 128, 0, False,
        'Number of bins to use for the histogram'),
        ('cmap', np.float32, DEFAULT_COLORMAP, 2, False,
        'Colormap array (N_samplesx4) to use for display'),
        ('vmin', np.float32, 0, 0, False,
        'Minimum intensity value to use for the colormap'),
        ('vmax', np.float32, 1, 0, False,
        'Maximum intensity value to use for the colormap'),
        ('projection', np.float32, 0, 0, False,
        'Thickness scale of projected layer (0: disable projection; 1: project all the way through k-space)'),
    ]))

@GLShapeDecorator
@ShapeDecorator
class Diffraction(DiffractionBase, GLPrimitive):
    shaders = {}

    shaders['vertex'] = """
    precision highp float;

    // u_num_steps is defined in the prelude; see functions below
    uniform mat4 camera;
    uniform vec4 rotation;
    uniform mat3 u_box_scaling;
    uniform vec3 u_fft_step;
    uniform float projection;

    attribute vec2 image;

    varying vec3 v_test_texcoord;
    varying vec3 v_fft_step;

    vec3 rotate(vec3 point, vec4 quat)
    {
        vec3 result = (quat.x*quat.x - dot(quat.yzw, quat.yzw))*point;
        result += 2.0*quat.x*cross(quat.yzw, point);
        result += 2.0*dot(quat.yzw, point)*quat.yzw;
        return result;
    }

    void main()
    {
        vec4 rotation_conj = vec4(-rotation.x, rotation.yzw);

        float step_factor = 0.5/float(u_num_steps);
        vec2 lambda = (image + 1.0)*0.5;
        vec2 texcoord = lambda*(1.0 - step_factor) + (1.0 - lambda)*step_factor*3.0;

        float center = step_factor*(float(u_num_steps) + 1.0);
        vec3 test_texcoord = vec3(texcoord, center);
        test_texcoord -= center;
        test_texcoord = u_box_scaling*rotate(test_texcoord, rotation_conj);
        test_texcoord += center;
        v_test_texcoord = test_texcoord;

        v_fft_step = projection*u_box_scaling*rotate(u_fft_step, rotation_conj);

        vec4 position = camera*vec4(0.5*image, 0.0, 1.0);
        gl_Position = vec4(position.xy, 0.0, 1.0);
    }
    """

    shaders['fragment'] = """
    precision highp float;

    varying vec3 v_test_texcoord;
    varying vec3 v_fft_step;

    uniform FFT_TYPE u_fft;
    uniform sampler2D u_cmap;
    // u_num_steps is defined in the prelude; see functions below
    uniform float vmin;
    uniform float vmax;
    uniform float projection;

    void main()
    {
        vec3 fft_delta = vec3(0.0, 0.0, 0.0);

        vec2 accumulator = FFT_SAMPLE(u_fft, v_test_texcoord).xy;
        for(int i = 0; i < 1024; i++)
        {
            if(2*i >= u_num_steps)
                break;

            fft_delta += v_fft_step;
            accumulator += FFT_SAMPLE(u_fft, v_test_texcoord - fft_delta).xy;
            accumulator += FFT_SAMPLE(u_fft, v_test_texcoord + fft_delta).xy;
        }

        float val = dot(accumulator, accumulator);

        val /= 2.0*float(u_num_steps);
        val = log(1.0 + val);
        val *= 1024.0*mix(0.05, 1.0, projection);
        val -= vmin;
        val /= vmax - vmin;

        gl_FragColor = texture2D(u_cmap, vec2(val, val));
    }
    """

    _vertex_attribute_names = ['image']

    _ATTRIBUTES = list(itertools.starmap(ShapeAttribute, [
        ('positions', np.float32, (0, 0, 0), 2, True,
        'Real-space coordinates for each particle'),
        ('box', np.float32, (1, 1, 1, 0, 0, 0), 1, False,
        'Box parameters to use for FFT scaling using the HOOMD schema (Lx, Ly, Lz, xy, xz, yz)'),
        ('size', np.uint32, 128, 0, False,
        'Number of bins to use for the histogram'),
        ('sigma', np.float32, 0, 0, False,
        'Blur length scale'),
    ]))

    _GL_UNIFORMS = list(itertools.starmap(ShapeAttribute, [
        ('camera', np.float32, np.eye(4), 2, False,
        'Internal: 4x4 Camera matrix for world projection'),
        ('rotation', np.float32, (1, 0, 0, 0), 1, False,
        'Internal: rotation to be applied to each scene as a quaternion'),
        ('vmin', np.float32, 0, 0, False,
        'Minimum intensity value to use for the colormap'),
        ('vmax', np.float32, 1, 0, False,
        'Maximum intensity value to use for the colormap'),
        ('u_box_scaling', np.float32, np.eye(3), 2, False,
        'Internal: Step size scaling matrix'),
        ('projection', np.float32, 0, 0, False,
        'Thickness scale of projected layer (0: disable projection; 1: project all the way through k-space)'),
    ]))

    def __init__(self, *args, **kwargs):
        GLPrimitive.__init__(self)
        DiffractionBase.__init__(self, *args, **kwargs)

        if self._webgl:
            self._shader_substitutions['FFT_TYPE'] = 'sampler2D'
        else:
            self._shader_substitutions['FFT_TYPE'] = 'sampler3D'

    @property
    def cmap(self):
        return self._attributes['cmap']

    @cmap.setter
    def cmap(self, value):
        value = np.atleast_2d(value).reshape((1, -1, 4))
        self._dirty_uniforms.add('u_cmap')
        self._gl_uniforms['u_cmap'] = vispy.gloo.Texture2D(
            value, interpolation='linear')

    def make_prelude(self, config={}):
        result = [super().make_prelude(config)]
        result.append('precision highp float;')
        result.append('uniform int u_num_steps;')
        result.append('#define VISPY_IGNORED_UNIFORM uniform')

        result.append('#ifdef WEBGL')
        snippet = vispy.gloo.TextureEmulated3D._glsl_sample_linear
        for piece in ['$shape.x', '$shape.y', '$shape.z']:
            snippet = snippet.replace(piece, 'float(u_num_steps)')

        result.append('#define TEXTURE_R (1024/u_num_steps)')
        snippet = snippet.replace('$r', 'float(TEXTURE_R)')
        result.append('#define TEXTURE_C (u_num_steps/TEXTURE_R '
                      '+ int(fract(float(u_num_steps)/float(TEXTURE_R)) > 0.0))')
        snippet = snippet.replace('$c', 'float(TEXTURE_C)')
        result.append(snippet)

        result.append('#define FFT_SAMPLE sample')

        result.append('#else')

        result.append('#define FFT_SAMPLE texture3D')

        result.append('#endif')
        return '\n'.join(result)

    def update_arrays(self):
        if 'box' in self._dirty_attributes:
            matrix = plato.math.box_to_matrix(self.box).T
            matrix /= np.max(self.box[:3])
            self._dirty_uniforms.add('u_box_scaling')
            self._gl_uniforms['u_box_scaling'] = matrix

        update_fft = False
        if any(name in self._dirty_attributes for name in ['positions', 'box', 'size']):
            N = self.size
            points = plato.math.make_fractions(self.box, self.positions)

            bin_xyz = np.round(points*N).astype(np.uint32)
            bin_xyz %= N
            bin_index_basis = (1, N, N**2)
            bin_indices = np.dot(bin_xyz, bin_index_basis)
            histogram = np.bincount(bin_indices, minlength=N**3)
            histogram = histogram.reshape((N, N, N)).astype(np.float32)
            histogram /= len(points)

            histogram /= np.sqrt(N)

            self._gl_attributes['histogram_fft'] = np.fft.fftn(histogram)
            update_fft = True

            self._dirty_uniforms.add('u_fft_step')
            self._dirty_uniforms.add('u_num_steps')
            self._gl_uniforms['u_fft_step'] = (0, 0, 0.5/self.size)
            self._gl_uniforms['u_num_steps'] = self.size

        if 'sigma' in self._dirty_attributes or update_fft:
            fft = self._gl_attributes['histogram_fft']
            if self.sigma:
                self._gl_attributes['total_fft'] = scipy.ndimage.fourier_gaussian(fft, self.sigma*self.size)
            else:
                self._gl_attributes['total_fft'] = fft
            update_fft = True

        if update_fft:
            fft = self._gl_attributes['total_fft']
            fft = np.fft.fftshift(fft)

            fft = np.stack([
                fft.real.astype(np.float32),
                fft.imag.astype(np.float32),
                np.zeros_like(fft, dtype=np.float32)
            ], axis=-1)

            if self._webgl:
                TextureFFT = vispy.gloo.TextureEmulated3D
            else:
                TextureFFT = vispy.gloo.Texture3D

            self._dirty_uniforms.add('u_fft')
            self._gl_uniforms['u_fft'] = TextureFFT(
                fft, wrapping='clamp_to_edge', interpolation='linear')

        vertex_arrays = [np.array([(-1, -1), (1, -1), (1, 1), (-1, 1)], dtype=np.float32)]
        indices = np.array([(0, 1, 2), (0, 2, 3)], dtype=np.uint32)

        self._finalize_array_updates(indices, vertex_arrays)

        self._dirty_attributes.clear()

plato.draw.vispy.Diffraction = Diffraction
