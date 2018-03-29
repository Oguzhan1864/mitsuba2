"""
This file defines a set of distributions that will be checked using a Chi^2
statistical hypothesis test. The objective of this test is to ensure that the
distribution generated by a sample generator really matches the target
distribution. Tests are executed as part of the automated test suite, which
can be run using the following commands:

    $ source setpath.sh
    $ python -m pytest

They can also be executed in a visual manner using the warp visualizer utility

    $ source setpath.sh
    $ python -m mitsuba.ui.visualizer

Each entry of the DISTRIBUTIONS table is a tuple with the following entries:

    1. Name of the test

    2. An adapter that explains the domain of the distribution (see chi2.py)

    3. A nested tuple containing
        1. A sample generator
        2. A probability function

    4. A dictionary of settings that can be used to modify the test behavior

"""

from __future__ import division
from mitsuba.core import warp, float_dtype
from mitsuba.core.chi2 import SphericalDomain, PlanarDomain, LineDomain
from mitsuba.core.chi2 import (
    SpectrumAdapter, BSDFAdapter, MicrofacetAdapter,
    InteractiveMicrofacetBSDFAdapter)
from mitsuba.render import MicrofacetDistribution
from mitsuba.core import Bitmap, Thread
from mitsuba.core.warp import Linear2D0, Linear2D2
from mitsuba.test.util import fresolver_append_path
import numpy as np
import os


def deg2rad(value):
    return value * np.pi / 180

DEFAULT_SETTINGS   = {'sample_dim': 2, 'ires': 10, 'res': 101, 'parameters': []}
DEFAULT_SETTINGS_3 = {'sample_dim': 3, 'ires': 10, 'res': 101, 'parameters': []}


DISTRIBUTIONS = [
    ('Uniform square', PlanarDomain(np.array([[0, 1],
                                              [0, 1]])),
    (lambda x: x,
     lambda x: np.ones(x.shape[0])),
     DEFAULT_SETTINGS),

    ('Uniform triangle', PlanarDomain(np.array([[0, 1],
                                                [0, 1]])),
     (warp.square_to_uniform_triangle,
      warp.square_to_uniform_triangle_pdf),
     dict(DEFAULT_SETTINGS, res=100)),

    ('Tent function', PlanarDomain(np.array([[-1, 1],
                                             [-1, 1]])),
     (warp.square_to_tent,
      warp.square_to_tent_pdf),
     DEFAULT_SETTINGS),

    ('Uniform disk', PlanarDomain(),
     (warp.square_to_uniform_disk,
      warp.square_to_uniform_disk_pdf),
     DEFAULT_SETTINGS),

    ('Uniform disk (concentric)', PlanarDomain(),
     (warp.square_to_uniform_disk_concentric,
      warp.square_to_uniform_disk_concentric_pdf),
     DEFAULT_SETTINGS),

    ('Uniform sphere', SphericalDomain(),
     (warp.square_to_uniform_sphere,
      warp.square_to_uniform_sphere_pdf),
     DEFAULT_SETTINGS),

    ('Uniform hemisphere', SphericalDomain(),
     (warp.square_to_uniform_hemisphere,
      warp.square_to_uniform_hemisphere_pdf),
     DEFAULT_SETTINGS),

    ('Cosine hemisphere', SphericalDomain(),
     (warp.square_to_cosine_hemisphere,
      warp.square_to_cosine_hemisphere_pdf),
     DEFAULT_SETTINGS),

    ('Uniform cone', SphericalDomain(),
    (lambda sample, angle:
         warp.square_to_uniform_cone(sample, np.cos(deg2rad(angle))),
     lambda v, angle:
         warp.square_to_uniform_cone_pdf(v, np.cos(deg2rad(angle)))),
     dict(DEFAULT_SETTINGS,
         parameters=[
             ('Cutoff angle', [1e-4, 180, 20])
         ])),

    ('Beckmann distribution', SphericalDomain(),
    (lambda sample, value:
         warp.square_to_beckmann(sample,
             np.exp(np.log(0.05) * (1 - value) + np.log(1) * value)),
     lambda v, value:
         warp.square_to_beckmann_pdf(v,
             np.exp(np.log(0.05) * (1 - value) + np.log(1) * value))),
     dict(DEFAULT_SETTINGS,
         parameters=[
             ('Roughness', [0, 1, 0.6])
         ])),

    ('von Mises-Fisher distribution', SphericalDomain(),
     (warp.square_to_von_mises_fisher,
      warp.square_to_von_mises_fisher_pdf),
     dict(DEFAULT_SETTINGS,
         parameters=[
             ('Concentration', [0, 100, 10])
         ])),

    ('Rough fiber distribution', SphericalDomain(),
     (lambda sample, kappa, incl: warp.square_to_rough_fiber(
          sample, np.tile(np.array([np.sin(deg2rad(incl)), 0, np.cos(deg2rad(incl))], dtype=float_dtype), [sample.shape[0], 1]),
          np.tile(np.array([1, 0, 0], dtype=float_dtype), [sample.shape[0], 1]), kappa),
      lambda v, kappa, incl: warp.square_to_rough_fiber_pdf(
          v, np.tile([np.sin(deg2rad(incl)), 0, np.cos(deg2rad(incl))], [v.shape[0], 1]),
          np.tile([1, 0, 0], [v.shape[0], 1]), kappa)),
     dict(DEFAULT_SETTINGS,
         sample_dim=3,
         parameters=[
             ('Concentration', [0, 500, 10]),
             ('Inclination', [0, 90, 20])
         ])
    ),

    ('Spectrum: test', LineDomain([300.0, 700.0]),
     SpectrumAdapter("""<spectrum version="2.0.0" type="interpolated">
        <float name="lambda_min" value="400"/>
        <float name="lambda_max" value="650"/>
        <string name="values" value="1, 5, 3, 6"/>
      </spectrum>"""),
     dict(DEFAULT_SETTINGS, sample_dim=1)),

    ('Spectrum: d65', LineDomain([360.0, 830.0]),
     SpectrumAdapter('<spectrum version="2.0.0" type="d65"/>'),
     dict(DEFAULT_SETTINGS, sample_dim=1)),

    ('Spectrum: blackbody', LineDomain([360.0, 830.0]),
     SpectrumAdapter('<spectrum version="2.0.0" type="blackbody">'
                     '   <float name="temperature" value="%f"/>'
                     '</spectrum>'),
     dict(DEFAULT_SETTINGS,
          sample_dim=1,
          parameters=[
              ('Temperature', [0, 8000, 3000]),
          ])),

    ('Microfact: Beckmann, all, 0.5', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EBeckmann, 0.5, False),
     DEFAULT_SETTINGS),
    ('Microfact: Beckmann, all, 0.1', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EBeckmann, 0.1, False),
     DEFAULT_SETTINGS),

    ('Microfact: Beckmann, vis, 0.5', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EBeckmann, 0.5, True),
     dict(DEFAULT_SETTINGS,
         parameters=[('Angle of incidence', [0, 90, 30])])),
    ('Microfact: Beckmann, vis, 0.1', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EBeckmann, 0.1, True),
     dict(DEFAULT_SETTINGS,
         parameters=[('Angle of incidence', [0, 90, 30])])),

    ('Microfact: GGX, all, 0.5', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EGGX, 0.5, False),
     DEFAULT_SETTINGS),
    ('Microfact: GGX, all, 0.1', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EGGX, 0.1, False),
     DEFAULT_SETTINGS),

    ('Microfact: GGX, vis, 0.5', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EGGX, 0.5, True),
     dict(DEFAULT_SETTINGS,
         parameters=[('Angle of incidence', [0, 90, 30])])),
    ('Microfact: GGX, vis, 0.1', SphericalDomain(),
     MicrofacetAdapter(MicrofacetDistribution.EGGX, 0.1, True),
     dict(DEFAULT_SETTINGS,
         parameters=[('Angle of incidence', [0, 90, 30])])),

    ('Diffuse BSDF', SphericalDomain(),
     BSDFAdapter("diffuse", ''), DEFAULT_SETTINGS_3),

    ('Rough conductor BSDF - smooth', SphericalDomain(),
     BSDFAdapter("roughconductor", """
        <float name="alpha" value="0.05"/>
     """), DEFAULT_SETTINGS_3),
    ('Rough conductor BSDF - rough', SphericalDomain(),
     BSDFAdapter("roughconductor", """
        <float name="alpha" value="0.25"/>
     """), DEFAULT_SETTINGS_3),
    ('Rough conductor BSDF - rough - alternative wi', SphericalDomain(),
     BSDFAdapter("roughconductor", """
        <float name="alpha" value="0.25"/>
     """, wi=[0.970942, 0, 0.239316]), DEFAULT_SETTINGS_3),

    ('Rough conductor BSDF - interactive', SphericalDomain(),
     InteractiveMicrofacetBSDFAdapter("roughconductor", """
        <boolean name="sample_visible" value="false"/>
        <string name="distribution" value="beckmann"/>
    """), dict(DEFAULT_SETTINGS_3,
         parameters=[
             ('alpha_u', [0, 1, 0.2]),
             ('alpha_v', [0, 1, 0.2]),
             ('Theta', [0, np.pi, 0]),
             ('Phi', [0, 2*np.pi, 0])
     ])),
    ('Rough conductor BSDF - vis - interactive', SphericalDomain(),
     InteractiveMicrofacetBSDFAdapter("roughconductor", """
        <boolean name="sample_visible" value="true"/>
        <string name="distribution" value="beckmann"/>
    """), dict(DEFAULT_SETTINGS_3,
         parameters=[
             ('alpha_u', [0, 1, 0.2]),
             ('alpha_v', [0, 1, 0.2]),
             ('Theta', [0, np.pi, 0]),
             ('Phi', [0, 2*np.pi, 0])
     ])),

    # ('Rough plastic BSDF - smooth', SphericalDomain(),
    #  BSDFAdapter("roughplastic", """
    #     <float name="alpha" value="0.05"/>
    #     <spectrum name="specular_reflectance" value="0.7"/>
    #     <spectrum name="diffuse_reflectance" value="0.0"/>
    #  """), DEFAULT_SETTINGS_3),
    ('Rough plastic BSDF - rough', SphericalDomain(),
     BSDFAdapter("roughplastic", """
        <float name="alpha" value="0.25"/>
        <spectrum name="specular_reflectance" value="0.4"/>
        <spectrum name="diffuse_reflectance" value="0.9"/>
     """), DEFAULT_SETTINGS_3),
    ('Rough plastic BSDF - rough - alternative wi', SphericalDomain(),
     BSDFAdapter("roughplastic", """
        <float name="alpha" value="0.25"/>
        <spectrum name="specular_reflectance" value="0.4"/>
        <spectrum name="diffuse_reflectance" value="0.9"/>
     """, wi=[0.48666426,  0.32444284,  0.81110711]), DEFAULT_SETTINGS_3),

    ('Plastic BSDF', SphericalDomain(),
     BSDFAdapter("plastic", """
        <rgb name="specular_reflectance" value="1.0, 0.1, 0.1"/>
        <rgb name="diffuse_reflectance" value="0.5, 0.5, 1.0"/>
     """), DEFAULT_SETTINGS_3),
    ('Plastic BSDF - alternative wi', SphericalDomain(),
     BSDFAdapter("plastic", """
        <rgb name="specular_reflectance" value="1.0, 0.1, 0.1"/>
        <rgb name="diffuse_reflectance" value="0.5, 0.5, 1.0"/>
     """, wi=[0.48666426,  0.32444284,  0.81110711]), DEFAULT_SETTINGS_3),
]

@fresolver_append_path
def LinearWarp2D0Test():
    fr = Thread.thread().file_resolver()

    prefix = 'resources/data/tests/warp/'
    img0 = np.array(Bitmap(fr.resolve(prefix + 'small.png')), dtype=np.float32)
    d = Linear2D0(img0.squeeze())

    def sample_functor(sample, *args):
        return d.sample(sample, *args)[0]

    def pdf_functor(p, *args):
        return d.eval(p, *args)

    return sample_functor, pdf_functor


@fresolver_append_path
def LinearWarp2D2Test():
    fr = Thread.thread().file_resolver()

    prefix = 'resources/data/tests/warp/'
    img0 = np.array(Bitmap(fr.resolve(prefix + 'img0.png')), dtype=np.float32)
    img1 = np.array(Bitmap(fr.resolve(prefix + 'img1.png')), dtype=np.float32)
    img2 = np.array(Bitmap(fr.resolve(prefix + 'img2.png')), dtype=np.float32)
    img3 = np.array(Bitmap(fr.resolve(prefix + 'img3.png')), dtype=np.float32)

    tensor = np.full((2, 2, 512, 512), 0, dtype=np.float32)
    tensor[0, 0, :, :] = img0.squeeze()
    tensor[0, 1, :, :] = img1.squeeze()
    tensor[1, 0, :, :] = img2.squeeze()
    tensor[1, 1, :, :] = img3.squeeze()

    d = Linear2D2(tensor, [[0, 1], [0, 1]])

    def sample_functor(sample, *args):
        return d.sample(sample, *args)[0]

    def pdf_functor(p, *args):
        return d.eval(p, *args)

    return sample_functor, pdf_functor


DISTRIBUTIONS += [
    ('Hierarchical warp (small)',
     PlanarDomain(np.array([[0, 1], [0, 1]])),
     LinearWarp2D0Test(),
     DEFAULT_SETTINGS),
    ('Hierarchical warp (4D, big)',
     PlanarDomain(np.array([[0, 1], [0, 1]])),
     LinearWarp2D2Test(),
     dict(DEFAULT_SETTINGS,
         parameters=[
             ('param0', [0, 1, 0.5]),
             ('param1', [0, 1, 0.005])
         ]))
]
