# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        vis
# Purpose:
#
# Authors:     Maik Heistermann, Stephan Jacobi and Thomas Pfaff
#
# Created:     26.10.2011
# Copyright:   (c) Maik Heistermann, Stephan Jacobi and Thomas Pfaff 2011
# Licence:     The MIT License
#-------------------------------------------------------------------------------
#!/usr/bin/env python

"""
Visualisation
^^^^^^^^^^^^^

Standard plotting and mapping procedures

.. autosummary::
   :nosignatures:
   :toctree: generated/

   polar_plot
   cartesian_plot
   rhi_plot
   plot_scan_strategy
   plot_plan_and_vert
   plot_tseries

"""

# standard libraries
import os.path as path
import math

# site packages
import numpy as np
import pylab as pl
import matplotlib
from matplotlib import mpl
#from mpl_toolkits.basemap import Basemap, cm
from matplotlib.projections import PolarAxes, register_projection
from matplotlib.transforms import Affine2D, Bbox, IdentityTransform
from mpl_toolkits.axisartist import SubplotHost, ParasiteAxesAuxTrans, GridHelperCurveLinear
from mpl_toolkits.axisartist.grid_finder import FixedLocator
from mpl_toolkits.axes_grid1 import make_axes_locatable
from mpl_toolkits.axes_grid1 import axes_size as Size
import mpl_toolkits.axisartist.angle_helper as angle_helper
from matplotlib.ticker import NullFormatter, FuncFormatter
import matplotlib.dates as mdates
import matplotlib.font_manager as fm

# wradlib modules
import wradlib.georef as georef
import wradlib.util as util


class NorthPolarAxes(PolarAxes):
    '''
    A variant of PolarAxes where theta starts pointing north and goes
    clockwise.
    Obsolete since matplotlib version 1.1.0, where the same behaviour may
    be achieved with a reconfigured standard PolarAxes object.
    '''
    name = 'northpolar'

    class NorthPolarTransform(PolarAxes.PolarTransform):
        def transform(self, tr):
            xy   = np.zeros(tr.shape, np.float_)
            t    = tr[:, 0:1]
            r    = tr[:, 1:2]
            x    = xy[:, 0:1]
            y    = xy[:, 1:2]
            x[:] = r * np.sin(t)
            y[:] = r * np.cos(t)
            return xy

        transform_non_affine = transform

        def inverted(self):
            return NorthPolarAxes.InvertedNorthPolarTransform()

    class InvertedNorthPolarTransform(PolarAxes.InvertedPolarTransform):
        def transform(self, xy):
            x = xy[:, 0:1]
            y = xy[:, 1:]
            r = np.sqrt(x*x + y*y)
            theta = np.arctan2(y, x)
            return np.concatenate((theta, r), 1)

        def inverted(self):
            return NorthPolarAxes.NorthPolarTransform()

    def _set_lim_and_transforms(self):
        PolarAxes._set_lim_and_transforms(self)
        self.transProjection = self.NorthPolarTransform()
        self.transData = (
            self.transScale +
            self.transProjection +
            (self.transProjectionAffine + self.transAxes))
        self._xaxis_transform = (
            self.transProjection +
            self.PolarAffine(IdentityTransform(), Bbox.unit()) +
            self.transAxes)
        self._xaxis_text1_transform = (
            self._theta_label1_position +
            self._xaxis_transform)
        self._yaxis_transform = (
            Affine2D().scale(np.pi * 2.0, 1.0) +
            self.transData)
        self._yaxis_text1_transform = (
            self._r_label1_position +
            Affine2D().scale(1.0 / 360.0, 1.0) +
            self._yaxis_transform)

register_projection(NorthPolarAxes)


class PolarPlot(object):
    def __init__(self, ax=None, fig=None, axpos=111, **kwargs):
        if ax is None:
            if fig is None:
                # crate a new figure object
                fig = pl.figure(**kwargs)
            # plot on the axes object which was passed to this function
            try: # version working before matplotlib 1.1.0. may be removed some time
                ax = fig.add_subplot(axpos, projection="northpolar", aspect=1.)
            except AttributeError: # happens in new versions of matplotlib (v.1.1 and newer due to changes to the transforms api)
                # but then again, we have new functionality obsolescing the old
                # northpolar axes object
                ax = fig.add_subplot(axpos, projection="polar", aspect=1.)
                ax.set_theta_direction(-1)
                ax.set_theta_zero_location("N")

        self.fig = fig
        self.ax = ax
        self.cmap = 'jet'
        self.norm = None

    def set_cmap(self, cmap, classes=None):
        if classes is None:
            self.cmap = cmap
        else:
            mycmap = pl.get_cmap(cmap, lut=len(classes))
            mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(classes)-1) ))
            norm   = mpl.colors.BoundaryNorm(classes, mycmap.N)
            self.cmap = mycmap
            self.norm = norm


    def plot(self, data, R=1., theta0=0, **kwargs):
        n_theta, n_r = data.shape
        theta = np.linspace(0, 2*np.pi, n_theta+1)
        r = np.linspace(0., R, n_r+1)

        data = np.transpose(data)
        data = np.roll(data, theta0, axis=1)

        circle = self.ax.pcolormesh(theta, r, data, rasterized=True, cmap=self.cmap,
                           norm=self.norm, **kwargs)
        return circle


    def colorbar(self, *args, **kwargs):
        #if not kwargs.has_key('shrink'):
        #    kwargs['shrink'] = 0.75
        cbar = pl.colorbar(*args, **kwargs)
        return cbar


    def title(self, s, *args, **kwargs):
        l = self.ax.set_title(s, *args, **kwargs)
        pl.draw_if_interactive()
        return l


    def grid(self, b=None, which='major', **kwargs):
        ret =  self.ax.grid(b, which, **kwargs)
        pl.draw_if_interactive()
        return ret


def polar_plot2(data, title='', unit='', saveto='', fig=None, axpos=111, R=1., theta0=0, colormap='jet', classes=None, extend='neither', **kwargs):
    pp = PolarPlot(fig=fig, axpos=axpos, figsize=(8,8))
    pp.set_cmap(colormap, classes=classes)
    circle = pp.plot(data, R=R, theta0=theta0, **kwargs)
    pp.grid(True)
    cbar = pp.colorbar(circle, shrink=0.75, extend=extend)
    cbar.set_label('('+unit+')')
    pp.title(title)
    if saveto=='':
        # show plot
        pl.show()
        if not pl.isinteractive():
            # close figure eplicitely if pylab is not in interactive mode
            pl.close()
    else:
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()


def polar_plot(data, title='', unit='', saveto='', fig=None, axpos=111, R=1., theta0=0, colormap='jet', classes=None, extend='neither', **kwargs):
    """Plots data from a polar grid.

    The data must be an array of shape (number of azimuth angles, number of range bins).
    The azimuth angle of zero corresponds to the north, the angles are counted clock-wise forward.

    additional `kwargs` will be passed to the pcolormesh routine displaying
    the data.

    Parameters
    ----------
    data : 2-d array
        polar grid data to be plotted
        1st dimension must be azimuth angles, 2nd must be ranges!
    title : string
        a title of the plot
    unit : string
        the unit of the data which is plotted
    saveto : string - path of the file in which the figure should be saved
        if string is empty, no figure will be saved and the plot will be
        sent to screen
    fig : matplotlib axis object
        if None, a new matplotlib figure will be created, otherwise we plot on ax
    axpos : an integer or a string
        correponds to the positional argument of matplotlib.figure.add_subplot
    R : float
        maximum range
    theta0 : integer
        azimuth angle which corresponds to the first slice of the dataset
        (normally corresponds to 0)
    colormap : string
        choose between the colormaps "jet" (per default) and "spectral"
    classes : sequence of numerical values
        class boundaries for plotting
    extend : string
        determines the behaviour of the colorbar: default value 'neither' produces
        a standard colorbar, 'min' and 'max' produces an arrow at the minimum or
        maximum end, respectively, and 'both' produces an arrow at both ends. If
        you use class boundaries for plotting, you should typically use 'both'.

    """
    n_theta, n_r = data.shape
    theta = np.linspace(0, 2*np.pi, n_theta+1)
    r = np.linspace(0., R, n_r+1)

    data = np.transpose(data)
    data = np.roll(data, theta0, axis=1)

    # plot as pcolormesh
    if fig==None:
        # crate a new figure object
        fig = pl.figure(figsize=(8,8))
        try: # version working before matplotlib 1.1.0. may be removed some time
            ax = fig.add_subplot(111, projection="northpolar", aspect=1.)
        except AttributeError: # happens in new versions of matplotlib (v.1.1 and newer due to changes to the transforms api)
            # but then again, we have new functionality obsolescing the old
            # northpolar axes object
            ax = fig.add_subplot(111, projection="polar", aspect=1.)
            ax.set_theta_direction(-1)
            ax.set_theta_zero_location("N")
    else:
        # plot on the axes object which was passed to this function
        try: # version working before matplotlib 1.1.0. may be removed some time
            ax = fig.add_subplot(axpos, projection="northpolar", aspect=1.)
        except AttributeError: # happens in new versions of matplotlib
            # but then again, we have new functionality obsolescing the old
            # northpolar axes object
            ax = fig.add_subplot(axpos, projection="polar", aspect=1.)
            ax.set_theta_direction(-1)
            ax.set_theta_zero_location("N")
    if classes==None:
        # automatic color normalization by vmin and vmax (not recommended)
        circle = ax.pcolormesh(theta, r, data,rasterized=True, cmap=colormap, **kwargs)
    else:
        # colors are assigned according to class boundaries and colormap argument
        mycmap = pl.get_cmap(colormap, lut=len(classes))
        mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(classes)-1) ))
        norm   = mpl.colors.BoundaryNorm(classes, mycmap.N)
        circle = ax.pcolormesh(theta, r, data,rasterized=True, cmap=mycmap, norm=norm, **kwargs)
    pl.grid(True)
    cbar = pl.colorbar(circle, shrink=0.75, extend=extend)
    cbar.set_label('('+unit+')')
    pl.title(title)
    if saveto=='':
        # show plot
        pl.show()
        if not pl.isinteractive():
            # close figure eplicitely if pylab is not in interactive mode
            pl.close()
    else:
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()


class CartesianPlot(object):
    def __init__(self, ax=None, fig=None, axpos=111, **kwargs):
        if ax is None:
            if fig is None:
                # create a new figure object
                fig = pl.figure(**kwargs)
            # plot on the axes object which was passed to this function
            ax = fig.add_subplot(axpos, aspect=1.)

        self.fig = fig
        self.ax = ax
        self.cmap = 'jet'
        self.norm = None

    def set_cmap(self, cmap, classes=None):
        if classes is None:
            self.cmap = cmap
        else:
            mycmap = pl.get_cmap(cmap, lut=len(classes))
            mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(classes)-1) ))
            norm   = mpl.colors.BoundaryNorm(classes, mycmap.N)
            self.cmap = mycmap
            self.norm = norm


    def plot(self, data, x, y, **kwargs):

        grd = self.ax.pcolormesh(x,y,data,rasterized=True, cmap=self.cmap,
                          norm=self.norm, **kwargs)
        return grd


    def colorbar(self, *args, **kwargs):
        #if not kwargs.has_key('shrink'):
        #    kwargs['shrink'] = 0.75
        cbar = pl.colorbar(*args, **kwargs)
        return cbar


    def title(self, s, *args, **kwargs):
        l = self.ax.set_title(s, *args, **kwargs)
        pl.draw_if_interactive()
        return l


    def grid(self, b=None, which='major', **kwargs):
        ret =  self.ax.grid(b, which, **kwargs)
        pl.draw_if_interactive()
        return ret



def cartesian_plot(data, x=None, y=None, title='', unit='', saveto='', fig=None, axpos=111, colormap='jet', classes=None, extend='neither', **kwargs):
    """Plots data from a cartesian grid.

    The data must be an array of shape (number of rows, number of columns).

    additional `kwargs` will be passed to the pcolormesh routine displaying
    the data.

    Parameters
    ----------
    data : 2-d array
        regular cartesian grid data to be plotted
        1st dimension must be number of rows, 2nd must be number of columns!
    title : string
        a title of the plot
    unit : string
        the unit of the data which is plotted
    saveto : string - path of the file in which the figure should be saved
        if string is empty, no figure will be saved and the plot will be
        sent to screen
    fig : matplotlib axis object
        if None, a new matplotlib figure will be created, otherwise we plot on ax
    axpos : an integer or a string
        correponds to the positional argument of matplotlib.figure.add_subplot
    colormap : string
        choose between the colormaps "jet" (per default) and "spectral"
    classes : sequence of numerical values
        class boundaries for plotting
    extend : string
        determines the behaviour of the colorbar: default value 'neither' produces
        a standard colorbar, 'min' and 'max' produces an arrow at the minimum or
        maximum end, respectively, and 'both' produces an arrow at both ends. If
        you use class boundaries for plotting, you should typically use 'both'.

    """
    pp = CartesianPlot(fig=fig, axpos=axpos, figsize=(8,8))
    pp.set_cmap(colormap, classes=classes)
    if (x==None) and (y==None):
        x = np.arange(data.shape[0])
        y = np.arange(data.shape[1])
    grd = pp.plot(data, x, y, **kwargs)
    pp.grid(True)
    cbar = pp.colorbar(grd, shrink=0.75, extend=extend)
    cbar.set_label('('+unit+')')
    pp.title(title)
    if saveto=='':
        # show plot
        pl.show()
        if not pl.isinteractive():
            # close figure eplicitely if pylab is not in interactive mode
            pl.close()
    else:
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()


##class PolarBasemap():
##    '''
##    Plot a spatial points dataset as a map (or a time series of maps)
##
##    *STILL UNDER DEVLOPMENT!!!*
##
##    Parameters
##    ----------
##    data    : Dataset which should be plotted
##                if <dset> contains different time steps, one map will be generated for each time step
##    conf    : a config object
##    title   : a base title - other elements will be appended to this base title
##    bbox    : the bounding box of the entire map in lat/lon; if None, the specs will be read from the config file key 'bbox_map'
##    ncolors : number of colors in the colomap lookup table - will be overridden by the classes argument
##    classes : classes of the plotting variable for which colors should be homogenoeous - overrides ncolors!
##    cmap    : name of the default colormap in case no colormap is provided in the config file
##    ensstat : in case dset contains an ensemble Dimension, the statistic function with name <ensstat> will be used to remove the ensemble Dimension by applying ensstat along the ens Dimension
##                <ensstat> should be contained in numpy and be retrived by getattr(numpy, ensstat) and it should have an axis argument
##    saveto  : if None, the plots are shown on the screen - otherwise the figures are saved to directory <saveto>
##    '''
##    def __init__(self, polygons, sitecoords, r, az, title='', bbox=None, ncolors=10, classes=None, cmap='jet'):
##
##        # Georeferencing the radar data
##        polygons = georef.polar2polyvert(r, az, sitecoords)
##
##        # define spatial bounding box of the Basemap
##        if bbox==None:
##            self.bbox={'llcrnrlon':np.min(polygons[:,:,0]),
##                  'llcrnrlat':np.min(polygons[:,:,1]),
##                  'urcrnrlon':np.max(polygons[:,:,0]),
##                  'urcrnrlat':np.max(polygons[:,:,1])}
##        else:
##            self.bbox = bbox
##
##        # define class boundaries for plotting
##        if classes!=None:
##            self.classes = np.array(classes)
##        else:
##            self.classes = np.array([-100, 10, 20, 30, 40, 50, 60, 70])
##        self.ncolors = len(self.classes)
##
##        # define map center
##        lon0=sitecoords[1]
##        lat0=sitecoords[0]
##
##        # plot the Basemap
##        self.m = Basemap(llcrnrlon=self.bbox['llcrnrlon'],llcrnrlat=self.bbox['llcrnrlat'],
##                        urcrnrlon=self.bbox['urcrnrlon'],urcrnrlat=self.bbox['urcrnrlat'],
##                    resolution='i',projection='tmerc',lat_0=lat0, lon_0=lon0)
##
##        # draw parallels and meridians
####        self.m.drawmapboundary(fill_color='aqua')
##        # fill continents, set lake color same as ocean color.
####        self.m.fillcontinents(color='coral',lake_color='aqua')
##        self.m.drawcoastlines(color='white')
##        self.m.drawparallels(np.linspace(start=np.round(self.bbox['llcrnrlat']), stop=np.round(self.bbox['urcrnrlat']), num=3), labels=[1,0,0,0])
##        self.m.drawmeridians(np.linspace(start=np.round(self.bbox['llcrnrlon']), stop=np.round(self.bbox['urcrnrlon']), num=3), labels=[0,0,0,1])
##        # draw map scale
##        self.m.drawmapscale(lon=self.bbox['urcrnrlon']-0.2*(self.bbox['urcrnrlon']-self.bbox['llcrnrlon']), lat=self.bbox['llcrnrlat']+0.1*(self.bbox['urcrnrlat']-self.bbox['llcrnrlat']), lon0=lon0, lat0=lat0, length=50., units='km', barstyle='fancy')
##
##        polygons[:,:,0], polygons[:,:,1] = self.m(polygons[:,:,0], polygons[:,:,1])
##        self.polygons = polygons
##    ##    # read shapefile which defines the plotting locations as polygons
##    ##    s = m.readshapefile(conf['shapefile_locations'], 'datashp', drawbounds=False)
##    ##
##    ##    # read the other shapefiles (which are only plotted as lines)
##    ##    if conf.has_key('shapefiles_extra'):
##    ##        oshps = {}
##    ##        for key in conf['shapefiles_extra'].keys():
##    ##            oshps[key] = m.readshapefile(conf['shapefiles_extra'][key], key, linewidth=conf['shapefiles_lwds'][key], color=conf['shapefiles_colors'][key])
##
##        # define plotting colormap and normalization
##
##        #   the color map needs one entry less than class boundaries!
####        if unit=='p':
####            mycmap = pl.get_cmap(cmap, lut=len(classes)-2)
####            myclist= mycmap( np.arange(mycmap.N) ).tolist()
####            myclist.insert(0,(0,0,0))
####            self.mycmap = mpl.colors.ListedColormap(myclist)
####        else:
####            mycmap = pl.get_cmap(cmap, lut=len(classes))
####            self.mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(classes)-1) ))
##        self.mycmap = pl.get_cmap(cmap, lut=len(self.classes))
##        self.mycmap = mpl.colors.ListedColormap(self.mycmap( np.arange(len(self.classes)-1) ))
##
##        norm   = mpl.colors.BoundaryNorm(self.classes, self.mycmap.N)
##
##        # define colorbar (we use a dummy mappable object via imshow)
##        self.cbar = pl.colorbar(mappable=pl.imshow(np.repeat(self.classes,2).reshape((2,-1)),
##                    cmap=self.mycmap, norm = norm), orientation='vertical', shrink=0.8, extend='max')
####        self.cbar.set_label('('+unit+')')
##
##        # get current axes instance
##        self.ax = pl.gca()
##
##
####        plot_data_on_map(ax=ax, data=data.ravel(), dtime='', mycmap=mycmap,
####                    polygons=polygons, classes=classes, bbox=bbox, name=var, saveto=None)
####
####        pl.close()
##
##    def __call__(self, data, dtime='', varname='', varunit='', saveto=None):
##        '''
##        Takes care of the actual data plot for each time step (plotting coloured polygons)
##        ---
##        ax      : matplotlib axes instance on which to plot the polygons
##        data    : a data array which must be consistent with the number of polygons as given by polygons
##        dtime   : the datetime which defines the end of the period represented by data
##        mycmap  : a colormap as defined in the calling function
##        polygons: a numpay ndarray of shape (number of polygons, number of polygon corners)
##        bbox    : the map's bounding box
##        name    : the name of the dataset (normally a parameter such as <p> or <wc>)
##        dsettype: the dsettype of the Dataset the data comes from
##        saveto  : if None, the map will be pplotted to the screen, otherwise it will be saved to directory <saveto>
##        '''
##        # give each polygon of the shapefile <datashp> a fillcolor based on its value
##        facecolors = np.repeat(self.mycmap(0)[0:3], len(self.polygons) ).reshape((-1,3),order='F')
##
##        for i,classval in enumerate(self.classes[1:]):
##            colidx = np.where(data.ravel()>=classval)[0]
##            facecolors[colidx,:] = np.array(self.mycmap(i+1)[0:3])
##
##        # plot polygons using matplotlib PolyCollection
##        polycoll = mpl.collections.PolyCollection(self.polygons,closed=True, facecolors=facecolors,edgecolors=facecolors)
##        mainplot = self.ax.add_collection(polycoll, autolim=True)
##
##        # add title to plot
##    ##    pl.title( get_map_title(name, dsettype, dtime) )
##
##        # if no save directory is given, show plot on screen
##        if saveto==None:
##            pl.show()
##        else:
##            fname    = name + '_' + dtime.strftime('%Y%m%d%H%M%S') + '.png'
##            savepath = path.join(saveto, fname)
##            pl.savefig(savepath)
##        # remove the PolygonCollection from the axis (otherwise the axis object becomes successively overcrowded)
##        self.ax.collections.remove(polycoll)


##class Grid2Basemap():
##    """Plot gridded data on a background map
##
##    *STILL UNDER DEVELOPMENT!!!*
##
##    This class allows to plot gridded data (e.g. PPIs, CAPPIs, composites) on a background.
##    The background map (Basemap) can include country borders, coastlines, meridians
##    as well as user-defined shapefiles. The plot will appear as filled contours.
##
##    In order to plot user defined backgroud data such as points or shapefiles,
##    these have to be provided in "geographical projection", i.e. in lat/lon coordinates
##    based on WGS84. You can use any GIS for this task. Shapefiles are then passed
##    to the constructor by providing a list of file paths in the argument *shpfiles*
##    (see `Parameters`).
##
##    Using Grid2Basemap(...), the background map is plotted. The actual data is plotted
##    by using the ``plot`` method. This procedure allows to repeatedly plot data on
##    a map (e.g. a time series) without each time plotting the background again. This
##    will save a huge amount of processing time if a large number of images is plotted
##    over the same background.
##
##    Parameters
##    ----------
##    bbox : dictionary
##        the bounding box of the entire map in lat/lon
##    classes : list of floats
##        classes of the plotting variable for which colors should be homogenoeous
##    unit : string
##    points : dictionary
##    shpfiles : list of strings
##        paths to shapefiles which will be plotted as map background
##    cmap : name of the default colormap in case no colormap is provided in the config file
##
##    """
##    def __init__(self, bbox, classes, unit='', points={}, cmap=cm.s3pcpn, shpfiles=[], **kwargs):
##
##        # Remember keyword args
##        self.bbox = bbox
##        self.classes = np.array(classes)
##        self.mycmap = cmap
##
##        # define map center
##        lon0=(bbox['llx']+bbox['urx'])/2
##        lat0=(bbox['lly']+bbox['ury'])/2
##
##        fig = pl.figure(figsize=(12,12))
##
##        ax = fig.add_subplot(111)
##
##        # plot the Basemap
##        self.m = Basemap(llcrnrlon=self.bbox['llx'],llcrnrlat=self.bbox['lly'],
##                        urcrnrlon=self.bbox['urx'],urcrnrlat=self.bbox['ury'],
##                    resolution='h',projection='tmerc',lat_0=lat0, lon_0=lon0, ax=ax)
##
##        # draw nice stuff
##        self.m.fillcontinents(color='grey', zorder=0)
##        self.m.drawcoastlines(color="white", linewidth=1.5)
##        self.m.drawparallels(np.linspace(start=np.round(self.bbox['lly']), stop=np.round(self.bbox['ury']), num=3), labels=[1,0,0,0])
##        if "meridians_at" in kwargs.keys():
##            meridians_at = kwargs["meridians_at"]
##        else:
##            meridians_at = np.linspace(start=np.round(self.bbox['llx']), stop=np.round(self.bbox['urx']), num=3)
##        self.m.drawmeridians(meridians_at, labels=[0,0,0,1])
##        # draw map scale
##        #   map scale locations
##        scalelon = self.bbox['urx']-0.2*(self.bbox['urx']-self.bbox['llx'])
##        scalelat = self.bbox['lly']+0.1*(self.bbox['ury']-self.bbox['lly'])
##        #   update map scale locations based on kwargs
##        if "scalelocation" in kwargs.keys():
##            if kwargs["scalelocation"]=="topright":
##                scalelon = self.bbox['urx']-0.2*(self.bbox['urx']-self.bbox['llx'])
##                scalelat = self.bbox['lly']+0.9*(self.bbox['ury']-self.bbox['lly'])
##        #   draw map scale
##        self.m.drawmapscale(lon=scalelon, lat=scalelat, lon0=lon0, lat0=lat0, length=50., units='km', barstyle='fancy', fontsize=11)
##
##        # read the other shapefiles (which are only plotted as lines)
##        for shp in shpfiles:
##            shp_info = self.m.readshapefile(shp, "name", linewidth=1.5, color="orange")
##
##        # draw points
##        markers = ['wo',"ws"]
##        for i,name in enumerate(points.keys()):
##            x, y =self.m(points[name]["lon"], points[name]["lat"])
##            pl.plot(x,y,markers[i], markersize=7)
##            try:
##                for j, locname in enumerate(points[name]["names"]):
##                    if (x[j]>self.m.llcrnrx) and (x[j]<self.m.urcrnrx) and (y[j]>self.m.llcrnry) and (y[j]<self.m.urcrnry):
##                        pl.text(x[j]+1000.,y[j]+1000.,locname, color="white", fontweight="bold")
##            except:
##                pass
##
##        # define colorbar (we use a dummy mappable object via imshow)
##        self.cbar = pl.colorbar(mappable=pl.contourf(np.repeat(self.classes,2).reshape((2,-1)), self.classes, cmap=self.mycmap),
##                    orientation='horizontal', shrink=1., extend='max', fraction=0.05, pad=0.05)
##        self.cbar.set_label('('+unit+')')
##
##
##    def plot(self, lon, lat, data, title='', saveto=None):
##        """Plot the data on the map background
##
##        Parameters
##        ----------
##        lon : array of longitudes
##        lat : array of latitudes
##        data : data array of shape (number of longitudes, number of latitudes)
##        title : figure title
##        saveto : string to a directory where figures should be stored
##
##        """
##        # add title plot
##        pl.title( title)
##        # get map coordinates
##        x, y =self.m(lon, lat)
##        # plot data
##        cs = self.m.contourf(x,y,data,self.classes, cmap=self.mycmap)
##
##        # if no save directory is given, show plot on screen
##        if saveto==None:
##            pl.draw()
##        else:
##            if title=='':
##                fname = "radarfig.png"
##            else:
##                fname    = title.replace(" ", "").replace("\n", "").replace(":","").strip() + '.png'
##            savepath = path.join(saveto, fname)
##            pl.savefig(savepath)
##        # remove data plot from the axis (otherwise the axis object becomes successively overcrowded)
##        for coll in cs.collections:
##            pl.gca().collections.remove(coll)


def get_tick_vector(vrange,vres):
    """Calculates Vector for tickmarks for function create_curvilinear_axes.

    Calculates tickmarks according to value range and wanted resolution. If no resolution is given,
    standard values [100., 50., 25., 20., 10., 5., 2.5, 2., 1., 0.5, 0.25, 0.2] are used.
    The number of tickmarks is normally between 5 and 10.

    Parameters
    ----------
    vrange : value range (first and last tickmark)
    vres : array of tick resolution (empty list, single value, multiple values)

    Returns
    ----------
    output : array of tickmarks

    """

    x = vrange[1]-vrange[0]

    if not vres:
        for div in [100.,50.,20.,10.,5.,2.5,2.,1.,0.5,0.25,0.2]:
            cnt = x/div
            if cnt >= 5:
                rem = np.mod(x,div)
                break
    else:
        if vres.size > 1:
            for div in vres:
                cnt = x/div
                if cnt >= 5:
                    rem = np.mod(x,div)
                    break
        elif vres.size == 1:
            cnt = x/vres
            rem = np.mod(x,vres)

    return np.linspace(vrange[0],vrange[1]-rem,num=cnt+1)

def create_curvilinear_axes(fig, **kwargs):
    """Creates Axis with Parasite Axis for curvilinear grid.

    Parameters
    ----------
    fig : figure object where to create axes
    **kwargs : some axis properties
       ['R','H','r_res','h_res', 'a_res', 'xtitle',  xunit, yunit, 'ytitle', 'atitle', 'title']

    """

    # get and process arguments
    x_range = kwargs.get('R')
    xd = x_range[1]-x_range[0]
    y_range = kwargs.get('H')
    yd = y_range[1]-y_range[0]
    axpos = kwargs.get('axpos')

    x_res = np.array(kwargs.get('r_res', 0.))
    y_res = np.array(kwargs.get('h_res', 0.))
    print(x_res, y_res)
    a_res = kwargs.get('a_res', 10.)
    xunit = kwargs.get('xunit', '')
    yunit = kwargs.get('yunit', '')
    xtitle = kwargs.get('xtitle','Range') + ' ('+xunit+')'
    ytitle = kwargs.get('ytitle','Height') + ' ('+yunit+')'
    atitle = kwargs.get('atitle','$Angle$')# ($^{\circ}$)')
    title = kwargs.get('title','Range Height Indicator')

    # get tickmark vectors for x and y
    rad = get_tick_vector(x_range[0:2], x_res)
    hgt = get_tick_vector(y_range, y_res)

    # construct transform
    tr = Affine2D().scale(np.pi/180, 1.) + PolarAxes.PolarTransform()

    # build up curvilinear grid
    extreme_finder = angle_helper.ExtremeFinderCycle(20, 20,
                                                     lon_cycle = 100,
                                                     lat_cycle = None,
                                                     lon_minmax = None,
                                                     lat_minmax = (0, np.inf),
                                                     )
    grid_locator1 = angle_helper.LocatorD(a_res)
    tick_formatter1 = angle_helper.FormatterDMS()
    grid_locator2 = FixedLocator([i for i in rad])
    grid_helper = GridHelperCurveLinear(tr,
                                        extreme_finder=extreme_finder,
                                        grid_locator1=grid_locator1,
                                        grid_locator2=grid_locator2,
                                        tick_formatter1=tick_formatter1,
                                        tick_formatter2=None,
                                        )

    # generate Axis
    ax1 = SubplotHost(fig, axpos , grid_helper=grid_helper)

    # make ticklabels of right and top axis visible.
    ax1.axis["right"].major_ticklabels.set_visible(True)
    ax1.axis["top"].major_ticklabels.set_visible(True)
    # but set tickmarklength to zero for better presentation
    ax1.axis["right"].major_ticks.set_ticksize(0)
    ax1.axis["top"].major_ticks.set_ticksize(0)

    # make ticklabels of right and top axis unvisible,
    # because we are drawing them
    ax1.axis["left"].major_ticklabels.set_visible(False)
    ax1.axis["bottom"].major_ticklabels.set_visible(False)
    # and also set tickmarklength to zero for better presentation
    ax1.axis["left"].major_ticks.set_ticksize(0)
    ax1.axis["bottom"].major_ticks.set_ticksize(0)

    # let right and top axis shows ticklabels for 1st coordinate (angle)
    ax1.axis["right"].get_helper().nth_coord_ticks=0
    ax1.axis["top"].get_helper().nth_coord_ticks=0

    # draw grid, tickmarks and ticklabes for left (y) and bottom (x) axis
    for xmaj in rad:
        ax1.axvline(x=xmaj,color='k', ls=':')
        if np.equal(np.mod(xmaj, 1), 0):
            xmaj = np.int(xmaj)
        ax1.text(xmaj,-yd/50.+y_range[0],str(xmaj), va='top', ha='center')
        line = mpl.lines.Line2D([xmaj,xmaj],[-yd/80.+y_range[0], y_range[0]], color='k')
        line.set_clip_on(False)
        ax1.add_line(line)

    for ymaj in hgt:
        ax1.axhline(y=ymaj,color='k', ls=':')
        if np.equal(np.mod(ymaj, 1), 0):
            ymaj = np.int(ymaj)
        ax1.text(-xd/80.+x_range[0],ymaj,str(ymaj).rjust(4), va='center', ha='right')
        line = mpl.lines.Line2D([-xd/130.+x_range[0],x_range[0]],[ymaj, ymaj], color='k')
        line.set_clip_on(False)
        ax1.add_line(line)

    # add axis to figure
    fig.add_subplot(ax1)

    # plot xy-axis labels and title
    ax1.text(-xd/15.+x_range[0],yd/2.0+y_range[0],ytitle, va='center', ha='right', rotation='vertical')
    ax1.text(xd/2.0+x_range[0],-yd/15.+y_range[0],xtitle, va='top', ha='center')
    # there is no "convenient" position for the "angle" label, maybe we dont need it at all
    # ax1.text(x_range[1],y_range[1] + yd/21.,atitle, va='top', ha='right')

    # plot axis title
    ax1.set_title(title)
    (tx,ty) = ax1.title.get_position()
    ax1.title.set_y(1.05 * ty)

    # generate and add parasite axes with given transform
    ax2 = ParasiteAxesAuxTrans(ax1, tr, "equal")
    # note that ax2.transData == tr + ax1.transData
    # Anthing you draw in ax2 will match the ticks and grids of ax1.
    ax1.parasites.append(ax2)

    ax1.set_xlim(x_range[0], x_range[1])
    ax1.set_ylim(y_range[0], y_range[1])
    ax1.grid(True)

    return ax1, ax2


def rhi_plot(data, **kwargs):
    """Returns figure and pylab object of plotted data from a polar grid as an RHI (Range Height Indicator).

    Plotting need to be done outside wradlib

    The data must be an array of shape (number of azimuth angles, number of range bins).
    The azimuth angle of 0 degrees corresponds to y-axis = 0 (east direction)
    The azimuth angle of 90 degrees corresponds to y-axis = 0 (north direction)
    The azimuth the angles are counted counter-clock-wise forward.

    Additional `myargs` are extracted from `kwargs`, processed and/or passed
    to the create_curvilinear_axes routine

    Additional remaining `kwargs` will be passed to the pcolormesh routine displaying
    the data. Be careful!

    Parameters
    ----------
    data : 2-d array
        polar grid data to be plotted
        1st dimension must be azimuth angles, 2nd must be ranges!

    Keyword arguments:

    R : tuple of array of float and unit string
        [display min range, display max range, data max range}, unit string
        defaults to [0, data.shape range, data.shape range], empty string
    H : array of array float and unit string
        [display min height, display max height], unit string
        defaults to [0,data.shape range ], empty string
    theta_range: float array
        theta range (min, max) used to display data
    rad_range: float array
        radial range (min, max) used to display data
    r_res : float array of range (x) tick resolution (empty, single value, multiple values)
    h_res : float array of height (y) tick resolution (empty, single value, multiple values)
    a_res : float
         sets # of angle gridlines and labels, defaults to 8, wich means 10 deg resolution

    title : string
        a title of the plot, defaults to 'Range Height Indicator'
    xtitle : string
        x-axis label
        defaults to 'Range' or 'Range (km)' if R is given (mostly km)
    ytitle : string
        y-axis label
        defaults to 'Height' or 'Height (km)' if H is given (mostly km)
    atitle : string
        angle-axis label, not used at the moment, due to inconvenient placing
        defaults to '$Angle$')# ($^{\circ}$)'
    saveto : string - path of the file in which the figure should be saved
        if string is empty, no figure will be saved and the plot will be
        sent to screen
    fig : matplotlib axis object
        if None, a new matplotlib figure will be created, otherwise we plot
        on given figure
    figsize : width , hight tuple in inches
         defaults to (10,6)
    axpos : an integer or a string
        correponds to the positional argument of mpl_toolkits.axisartist.SubplotHost
        defaults to '111'
        TODO: if multiple plots are used, position and size of labels have to be corrected
        in source code
    colormap :  string
        choose the colormap ("Paired" per default)
    classes :   sequence of numerical values
        class boundaries for plotting
    unit : string
        the unit of the data which is plotted
    extend :    string
        determines the behaviour of the colorbar: default value 'neither' produces
        a standard colorbar, 'min' and 'max' produces an arrow at the minimum or
        maximum end, respectively, and 'both' produces an arrow at both ends. If
        you use class boundaries for plotting, you should typically use 'both'.

    Returns
    ----------
    fig : figure object, just for testing and in the case of multiplot
    pl : pylab object, just for testing and in the case of multiplot

    """

    n_theta, n_r = data.shape

    # process kwargs
    if kwargs:
        key = kwargs.keys()
        value = kwargs.values()
        myargs = dict(zip(key, value))
    else:
        myargs = {}

    myargs['R'] = R = myargs.pop('R',([0, n_r, n_r], ''))
    myargs['R'] = R[0]
    myargs['xunit'] = R[1]
    R = R[0]

    H = myargs.pop('H',([0, n_r], ''))
    myargs['H'] = H[0]
    myargs['yunit'] = H[1]
    H = H[0]

    axpos = myargs.pop('axpos', '111')
    myargs['axpos'] = axpos

    extend = myargs.pop('extend', 'neither')
    classes = myargs.pop('classes', None)
    figsize = myargs.pop('figsize', (10,6))
    fig = myargs.pop('fig', None)
    dunit = myargs.pop('dunit','')
    saveto = myargs.pop('saveto','')
    colormap = myargs.pop('colormap','Paired')

    theta_range = myargs.pop('theta_range', [0,90])
    rad_range = myargs.pop('rad_range', [0,R[2]])

    # remove existing myargs from kwargs
    # remaining kwargs are for pccolormesh routine
    key = ['R','H','r_res','h_res', 'a_res', 'xtitle', \
           'ytitle', 'atitle', 'title', 'figsize', \
           'theta_range','rad_range', 'fig', 'dunit', \
           'saveto','colormap', 'axpos', 'xunit', 'yunit']
    if kwargs:
        value = myargs.values()
        for k in key:
            if k in kwargs:
                kwargs.pop(k)

    # setup vectors
    theta = np.linspace( 0, np.pi/2 , n_theta) # for RHI
    r = np.linspace(0., R[2], n_r)
    theta = theta * 180. / np.pi
    data = np.transpose(data)

    #calculate indices for data range to be plotted
    ind_start = np.where(theta >= theta_range[0])
    ind_stop = np.where(theta <= theta_range[1])
    ind_start1 = ind_start[0][0]
    ind_stop1 = ind_stop[0][-1]
    ind_start = np.where(r >= rad_range[0])
    ind_stop = np.where(r <= rad_range[1])
    ind_start2 = ind_start[0][0]
    ind_stop2 = ind_stop[0][-1]

    # apply data ranges to arrays
    theta = theta[ind_start1:ind_stop1]
    r = r[ind_start2:ind_stop2]
    data = data[ind_start2:ind_stop2,ind_start1:ind_stop1]

    # create figure, grids etc
    if fig==None:
        # create a new figure object
        fig = pl.figure(figsize=figsize)
        ax, ax2 = create_curvilinear_axes(fig, **myargs)
    else:
        # plot on the axes object which was passed to this function
        ax, ax2 = create_curvilinear_axes(fig, **myargs)

    # create rectangular meshgrid of polar data
    X,Y = np.meshgrid(theta,r)

    # plot data to parasite axis
    if classes==None:
        # automatic color normalization by vmin and vmax (not recommended)
        circle = ax2.pcolormesh(X, Y, data, rasterized=True, cmap=colormap, **kwargs)#, vmin=-32., vmax=95.5)
    else:
        # colors are assigned according to class boundaries and colormap argument
        mycmap = pl.get_cmap(colormap, lut=len(classes))
        mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(classes)-1) ))
        norm   = mpl.colors.BoundaryNorm(classes, mycmap.N)
        circle = ax2.pcolormesh(X, Y, data, rasterized=True, cmap=mycmap, norm=norm, **kwargs)

    # plot colorbar
    cbar = fig.colorbar(circle, extend=extend)
    cbar.set_label('('+dunit+')')

    if saveto!='':
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()

    return fig, pl

class cg_plot(object):
    def __init__(self, ind=None, ax=None, fig=None, **kwargs):
        """Class for plotting curvilinear axes
        PPI (Plan Position Indicator) and RHI (Range Height Indicator) supported.

        For RHI:
            The data must be an array of shape (number of azimuth angles, number of range bins).
            The azimuth angle of 0 degrees corresponds to y-axis = 0 (east direction)
            The azimuth angle of 90 degrees corresponds to x-axis = 0 (north direction)
            The azimuth the angles are counted counter-clock-wise forward.

        For PPI:
            The data must be an array of shape (number of azimuth angles, number of range bins).
            The azimuth angle of 0 degrees corresponds to x-axis = 0 (north direction)
            The azimuth angle of 90 degrees corresponds to y-axis = 0 (east direction)
            The azimuth angles are counted clock-wise forward.

        Additional `myargs` are extracted from `kwargs`, processed and/or passed
        to the create_curvilinear_axes routine

        Additional remaining `kwargs` will be passed to the pcolormesh routine displaying
        the data. Be careful!

        Parameters
        ----------
        ind : string
                RHI or PPI indicating wanted product

            ax : actual axes

            fig : figure to plot on


        Keyword arguments:

        x_range :   tuple of array of float and unit string
                        [display min range, display max range, data max range}, unit string
                        defaults to [0, data.shape range, data.shape range], empty string
        y_range :   array of array float and unit string
                        [display min height, display max height], unit string
                        defaults to [0,data.shape range ], empty string
        theta_range: float array
                        theta range (min, max) used to display data
            radial_range: float array
                        radial range (min, max) used to display data
        data_range: float array
                        radial range (min, max) of the raw data array

        x_res : float array of range (x) tick resolution (empty, single value, multiple values)
        y_res : float array of height (y) tick resolution (empty, single value, multiple values)
        z_res : float array of colorbar (z) tick resolution (empty, single value, multiple values)
        a_res : float array of angle gridlines and labels, defaults to 8, wich means 10 deg resolution

            faxis : float
                if polar grid, angle where the first floating axis points to

            ftitle : string
            a title of the plot, defaults to None
        xtitle : string
            x-axis label
            defaults to None
        ytitle : string
            y-axis label
            defaults to None
        atitle : string
            angle-axis label, not used at the moment, due to inconvenient placing
            defaults to '$Angle$')# ($^{\circ}$)'
        saveto : string - path of the file in which the figure should be saved
            if string is empty, no figure will be saved and the plot will be
            sent to screen
        fig : matplotlib axis object
            if None, a new matplotlib figure will be created, otherwise we plot
            on given figure
        figsize : width , hight tuple in inches
            defaults to (10,6)
        axpos : an integer or a string
            correponds to the positional argument of mpl_toolkits.axisartist.SubplotHost
            defaults to '111'
            TODO: if multiple plots are used, position and size of labels have to be corrected
            in source code
        colormap :  string
            choose the colormap ("Paired" per default)
        classes :   sequence of numerical values
            class boundaries for plotting
        [x,y,z]unit : string
            the unit of the data which is plotted
        extend :    string
            determines the behaviour of the colorbar: default value 'neither' produces
            a standard colorbar, 'min' and 'max' produces an arrow at the minimum or
            maximum end, respectively, and 'both' produces an arrow at both ends. If
            you use class boundaries for plotting, you should typically use 'both'.

        Returns
        ----------
        class object

        """

        self.ind = ind
        self.ax = ax
        self.fig = fig
        self.mdpi = 80.0

        # process kwargs
        if kwargs:
            key = kwargs.keys()
            value = kwargs.values()
            myargs = dict(zip(key, value))
        else:
            myargs = {}

        # process myargs
        self.x_range = myargs.pop('x_range',None)
        self.y_range = myargs.pop('y_range',None)
        self.theta_range = myargs.pop('theta_range', None)
        self.radial_range = myargs.pop('radial_range',None)
        self.data_range = myargs.pop('data_range', None)

        self.float_axis = myargs.pop('faxis',45)

        self.xunit = myargs.pop('xunit',None)
        self.yunit = myargs.pop('yunit',None)
        self.zunit = myargs.pop('zunit',None)
        self.xtitle = None
        self.ytitle = None
        self.ztitle = None

        self.fsize = "5%"

        self.axpos = myargs.pop('axpos', '111')
        self.extend = myargs.pop('extend', None)
        self.classes = myargs.pop('classes', None)

        self.saveto = myargs.pop('saveto',None)
        self.colormap = myargs.pop('colormap','jet')


        if ind == 'PPI':
            self.ndeg = 360.
            self.theta_range = [0, 360]
            self.figsize = (8,8)
            self.aspect = 1.
            self.cbp = "5%"
            self.cbw = "5%"
        if ind == 'RHI':
            self.ndeg = 90.
            self.theta_range = [0, 90]
            self.figsize = (10,6)
            self.aspect = 0.
            self.cbp = "5%"
            self.cbw = "3%"

        self.x_res = np.array(kwargs.get('x_res', None))
        self.y_res = np.array(kwargs.get('y_res', None))
        self.z_res = np.array(kwargs.get('z_res', None))
        self.a_res = np.array(kwargs.get('a_res', None))


    def get_tick_vector(self, vrange, vres):
        """Calculates Vector for tickmarks.

        Calculates tickmarks according to value range and wanted resolution. If no resolution is given,
        standard values [100., 50., 25., 20., 10., 5., 2.5, 2., 1., 0.5, 0.25, 0.2] are used.
        The number of tickmarks is normally between 5 and 10.

        Parameters
        ----------
        vrange : value range (first and last tickmark)
        vres : array of tick resolution (empty list, single value, multiple values)

        Returns
        ----------
        output : array of tickmarks

        """

        x = vrange[1]- vrange[0]

        if not vres:
            for div in [200.,100.,50.,20.,10.,5.,2.5,2.,1.,0.5,0.25,0.2]:
                cnt = x/div
                if cnt >= 5:
                    rem = np.mod(x,div)
                    break
        else:
            if vres.size > 1:
                for div in vres:
                    cnt = x/div
                    if cnt >= 5:
                        rem = np.mod(x,div)
                        break
            elif vres.size == 1:
                cnt = x/vres
                rem = np.mod(x,vres)

        return np.linspace(vrange[0],vrange[1]-rem,num=cnt+1)

    def create_curvilinear_axes(self):
        """Creates Curvilinear Axes.

        All needed parameters are calculated in the init() and plot() routines. Normally called from plot().

        RHI - uses PolarAxes.PolarTransform
        PPI - uses NorthPolarAxes.NorthPolarTransform

        Parameters
        ----------
        None


        Returns
        ----------
        ax1 : axes object,
        ax2 : axes object, axes object, where polar data is plotted

        """

        if self.ind == 'RHI':
            tr = Affine2D().scale(np.pi/180, 1.) + PolarAxes.PolarTransform()
            # build up curvilinear grid
            extreme_finder = angle_helper.ExtremeFinderCycle(20, 20,
                                                         lon_cycle = 100,
                                                         lat_cycle = None,
                                                         lon_minmax = None,
                                                         lat_minmax = (0, np.inf),
                                                         )
            #grid_locator1 = angle_helper.LocatorD(self.a_res)
            if isinstance(self.a_res, int):
                grid_locator1 = FixedLocator([i for i in np.arange(0,91,self.a_res)])
            else:
                grid_locator1 = FixedLocator(self.a_res)
            tick_formatter1 = angle_helper.FormatterDMS()
            grid_locator2 = FixedLocator([i for i in self.rad])
            grid_helper = GridHelperCurveLinear(tr,
                                            extreme_finder=extreme_finder,
                                            grid_locator1=grid_locator1,
                                            grid_locator2=grid_locator2,
                                            tick_formatter1=tick_formatter1,
                                            tick_formatter2=None,
                                            )

            # generate Axis
            ax1 = SubplotHost(self.fig, self.axpos , grid_helper=grid_helper)
            # add axis to figure
            self.fig.add_subplot(ax1, aspect=self.aspect)
            ax1.set_aspect(self.aspect, adjustable='box-forced')

            # make ticklabels of right and top axis visible.
            ax1.axis["right"].major_ticklabels.set_visible(True)
            ax1.axis["top"].major_ticklabels.set_visible(True)
            # but set tickmarklength to zero for better presentation
            ax1.axis["right"].major_ticks.set_ticksize(0)
            ax1.axis["top"].major_ticks.set_ticksize(0)
            # let right and top axis shows ticklabels for 1st coordinate (angle)
            ax1.axis["right"].get_helper().nth_coord_ticks=0
            ax1.axis["top"].get_helper().nth_coord_ticks=0

        elif self.ind == 'PPI':

            tr = Affine2D().scale(np.pi/180, 1.) + NorthPolarAxes.NorthPolarTransform()
            # build up curvilinear grid
            extreme_finder = angle_helper.ExtremeFinderCycle(20, 20,
                                                         lon_cycle = 360.,
                                                         lat_cycle = None,
                                                         lon_minmax = (360.,0.),
                                                         lat_minmax = (0,self.radial_range[1]),
                                                         )
            if isinstance(self.a_res, int):
                grid_locator1 = FixedLocator([i for i in np.arange(0,359,self.a_res)])
            else:
                grid_locator1 = FixedLocator(self.a_res)
            tick_formatter1 = angle_helper.FormatterDMS()
            grid_locator2 = FixedLocator([i for i in self.rad])
            grid_helper = GridHelperCurveLinear(tr,
                                            extreme_finder=extreme_finder,
                                            grid_locator1=grid_locator1,
                                            grid_locator2=grid_locator2,
                                            tick_formatter1=tick_formatter1,
                                            tick_formatter2=None,
                                            )

            # generate Axis
            ax1 = SubplotHost(self.fig, self.axpos , grid_helper=grid_helper)
            # add axis to figure
            self.fig.add_subplot(ax1, aspect=self.aspect)
            ax1.set_aspect(self.aspect, adjustable='box-forced')
            #create floating axis,
            if self.float_axis:
                ax1.axis["lon"] = axis = ax1.new_floating_axis(0, self.float_axis)
                ax1.axis["lon"].set_visible(False)
                ax1.axis["lon"].major_ticklabels.set_visible(False)
                # and also set tickmarklength to zero for better presentation
                ax1.axis["lon"].major_ticks.set_ticksize(0)

##            # this is only for special plots with an "annulus"
##            ax1.axis["lon1"] = axis2 = ax1.new_floating_axis(1, self.data_range[0])
##            ax1.axis["lon1"].major_ticklabels.set_visible(False)
##            # and also set tickmarklength to zero for better presentation
##            ax1.axis["lon1"].major_ticks.set_ticksize(0)

            # this is in fact the outermost thick "ring"
            ax1.axis["lon2"] = axis = ax1.new_floating_axis(1, self.radial_range[1])
            ax1.axis["lon2"].major_ticklabels.set_visible(False)
            # and also set tickmarklength to zero for better presentation
            ax1.axis["lon2"].major_ticks.set_ticksize(0)

            # make ticklabels of right and bottom axis unvisible,
            # because we are drawing them
            ax1.axis["right"].major_ticklabels.set_visible(False)
            ax1.axis["top"].major_ticklabels.set_visible(False)

            # and also set tickmarklength to zero for better presentation
            ax1.axis["right"].major_ticks.set_ticksize(0)
            ax1.axis["top"].major_ticks.set_ticksize(0)

        # make ticklabels of left and bottom axis unvisible,
        # because we are drawing them
        ax1.axis["left"].major_ticklabels.set_visible(False)
        ax1.axis["bottom"].major_ticklabels.set_visible(False)

        # and also set tickmarklength to zero for better presentation
        ax1.axis["left"].major_ticks.set_ticksize(0)
        ax1.axis["bottom"].major_ticks.set_ticksize(0)

        # generate and add parasite axes with given transform
        ax2 = ParasiteAxesAuxTrans(ax1, tr, "equal")
        # note that ax2.transData == tr + ax1.transData
        # Anthing you draw in ax2 will match the ticks and grids of ax1.
        ax1.parasites.append(ax2)

        if self.ind == 'RHI':
            ax1.grid(True)

        return ax1, ax2

    def plot(self, data, **kwargs):
        """ plot data

        Parameters
        ----------
        data : 2-d array
            polar grid data to be plotted
            1st dimension must be azimuth angles, 2nd must be ranges!


        Returns
        ----------
        circle : plot object

        """
        n_theta, n_r = data.shape

        if self.ind == 'PPI':
            self.x_range = kwargs.pop('x_range',[-n_r, n_r])

        if self.ind == 'RHI':
            self.x_range = kwargs.pop('x_range',[0, n_r])


        self.y_range = kwargs.pop('y_range',[self.x_range[0], self.x_range[1]])

        self.xunit = kwargs.pop('xunit', None)
        self.yunit = kwargs.pop('yunit', None)
        self.x_res = np.array(kwargs.pop('x_res', self.x_res))
        self.y_res = np.array(kwargs.pop('y_res', self.y_res))
        self.a_res = kwargs.pop('a_res', 10.)
        self.float_axis = kwargs.pop('faxis', 30.)

        self.xtitle = kwargs.pop('xtitle', None)
        self.ytitle = kwargs.pop('ytitle', None)
        self.ftitle = kwargs.pop('ftitle', None)
        self.data_range = kwargs.pop('data_range',[0,self.x_range[1]])
        self.radial_range = kwargs.pop('radial_range',[0,self.x_range[1]])
        self.theta_range = kwargs.pop('theta_range',self.theta_range)


        self.aspect = kwargs.pop('aspect', self.aspect)

        #print('Data-Shape:',data.shape)

        # remove existing myargs from kwargs
        # remaining kwargs are for pccolormesh routine
        key = ['x_range','y_range','x_res','y_res', 'a_res', 'z_res', 'xtitle', \
            'ytitle', 'atitle', 'title', 'ztitle', 'figsize', \
            'theta_range','data_range', 'fig', 'zunit', \
            'saveto','colormap', 'axpos', 'xunit', 'yunit', 'extend']

        if kwargs:
            for k in key:
                if k in kwargs:
                    kwargs.pop(k)

        # setup theta and range vectors
        theta = np.linspace( 0, np.pi/180 * self.ndeg , n_theta)
        r = np.linspace(0., self.data_range[1], n_r)
        theta = theta * 180. / np.pi
        data = np.transpose(data)

        #calculate indices for data range to be plotted
        ind_start = np.where(theta >= self.theta_range[0])
        ind_stop = np.where(theta <= self.theta_range[1])
        ind_start1 = ind_start[0][0]
        ind_stop1 = ind_stop[0][-1]
        ind_start = np.where(r >= self.radial_range[0])
        ind_stop = np.where(r <= self.radial_range[1])
        ind_start2 = ind_start[0][0]
        ind_stop2 = ind_stop[0][-1]

        # apply data ranges to arrays
        theta = theta[ind_start1:ind_stop1+1] # +1 is to close the gap to 360deg
        r = r[ind_start2:ind_stop2]
        data = data[ind_start2:ind_stop2,ind_start1:ind_stop1]

        # gets vmin, vmax from raw data
        self.vmin = np.min(data)
        self.vmax = np.max(data)

        # gets dynamic of xrange and yrange
        self.xd = self.x_range[1]-self.x_range[0]
        self.yd = self.y_range[1]-self.y_range[0]
        xd = self.xd
        yd = self.yd
        x_range = self.x_range
        y_range = self.y_range

        # get range and hight (x and y) tick vectors
        self.rad = self.get_tick_vector(self.x_range, self.x_res)
        self.hgt = self.get_tick_vector(self.y_range, self.y_res)

        if self.ax is None:
            # create figure, and setup curvilienar grid etc
            if self.fig is None:
                # create a new figure object
                self.fig = pl.figure(figsize=(8,8),dpi=150)
                self.ax, self.ax2 = self.create_curvilinear_axes()
            else:
                # plot on the figure object which was passed to this function
                self.ax, self.ax2 = self.create_curvilinear_axes()

        #get dpi of fig, needed for automatic calculation of fontsize
        self.dpi = self.fig.get_dpi()
        #print("DPI:", self.dpi)


        # set x and y ax-limits
        self.ax.set_xlim(self.x_range[0], self.x_range[1])
        self.ax.set_ylim(self.y_range[0], self.y_range[1])

        # draw grid, tickmarks and ticklabes for left (y) and bottom (x) axis
        # left that out, user should use grid routines to draw ticks
        #self.xticks(self.x_res)
        #self.yticks(self.y_res)

        # plot xy-axis labels and title if already "published"
        if self.ytitle:
            ytitle = self.ytitle
            if self.yunit:
                ytitle = ytitle + ' ('+ self.yunit + ')'
            self.y_title(ytitle)
        if self.xtitle:
            xtitle = self.xtitle
            if self.xunit:
                xtitle = xtitle + ' ('+ self.xunit + ')'
            self.x_title(xtitle)
            # there is no "convenient" position for the "angle" label, maybe we dont need it at all
            # self.ax1.text(x_range[1],y_range[1] + yd/21.,self.atitle, va='top', ha='right')
        if self.ftitle:
            self.title(self.ftitle, ha="left", x = 0)

        # create rectangular meshgrid for polar data
        X,Y = np.meshgrid(theta,r)

        # plot data to parasite axis
        if self.classes==None:
            # automatic color normalization by vmin and vmax (not recommended) shading='flat', edgecolors='None'
            self.circle = self.ax2.pcolormesh(X, Y, data, rasterized=True, cmap=self.colormap, antialiased=False, **kwargs)
        else:
            # colors are assigned according to class boundaries and colormap argument
            mycmap = pl.get_cmap(self.colormap, lut=len(self.classes))
            mycmap = mpl.colors.ListedColormap(mycmap( np.arange(len(self.classes)-1) ))
            norm   = mpl.colors.BoundaryNorm(self.classes, mycmap.N)
            self.circle = self.ax2.pcolormesh(X, Y, data, rasterized=True, cmap=mycmap, norm=norm, **kwargs)

        return self.circle

    def get_fontsize(self, s, *args, **kwargs):
        """ gets fontsize according to given percentage and to actual axis size
            takes dpi of figure into account

        Parameters
        ----------
        s : string
            wanted "fontsize" in percentage of axis size

        Returns
        ----------
        fontsize in points

        """
        if s:
            if not isinstance(s, Size._Base):
                fsize = Size.from_any(s,
                                    fraction_ref=Size.AxesX(self.ax))
        else:
            s="5%"
            if not isinstance(s, Size._Base):
                fsize = Size.from_any(s,
                                    fraction_ref=Size.AxesX(self.ax))

        fs = self.ax.transData.transform((fsize.get_size(self.ax)[0],0))- self.ax.transData.transform((0,0))
        return  fs/(self.dpi/self.mdpi)

    def xticks(self, s, *args, **kwargs):
        """ turns xticks on/off

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """

        fsize = kwargs.pop('fsize','1.5%')
        ticklen = kwargs.pop('ticklen','1%')
        labelpad = kwargs.pop('labelpad','2%')

        if s == False:
            if hasattr(self, 'p_xticks'):
                if self.p_xticks:
                    for item in self.p_xticks:
                        item.remove()
                self.p_xticks = None
        else:
            if hasattr(self, 'p_xticks'):
                if self.p_xticks:
                    for item in self.p_xticks:
                        item.remove()
            self.p_xticks = []
            self.rad = self.get_tick_vector(self.x_range, np.array(s))

            fsize = self.get_fontsize(fsize)[0]
            ticklen = self.get_ypadding(ticklen, self.ax)
            labelpad = self.get_ypadding(labelpad, self.ax)

            for xmaj in self.rad:
                if np.equal(np.mod(xmaj, 1), 0):
                    xmaj = np.int(xmaj)
                text = self.ax.text(xmaj,-labelpad+self.y_range[0],str(xmaj), va='top', ha='center', fontsize=fsize)
                self.p_xticks.append(text)
                line = mpl.lines.Line2D([xmaj,xmaj],[-ticklen+self.y_range[0], self.y_range[0]], color='k')
                line.set_clip_on(False)
                self.ax.add_line(line)
                self.p_xticks.append(line)
            self.xgrid('update')

    def yticks(self, s, *args, **kwargs):
        """ turns yticks on/off

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """

        fsize = kwargs.pop('fsize','1.5%')
        ticklen = kwargs.pop('ticklen','1%')
        labelpad = kwargs.pop('labelpad','2%')

        if s == False:
            if hasattr(self, 'p_yticks'):
                if self.p_yticks:
                    for item in self.p_yticks:
                        item.remove()
                self.p_yticks = None
        else:
            if hasattr(self, 'p_yticks'):
                if self.p_yticks:
                    for item in self.p_yticks:
                        item.remove()
            self.p_yticks = []
            self.hgt = self.get_tick_vector(self.y_range, np.array(s))

            fsize = self.get_fontsize(fsize)[0]
            ticklen = self.get_xpadding(ticklen, self.ax)
            labelpad = self.get_xpadding(labelpad, self.ax)

            for ymaj in self.hgt:
                if np.equal(np.mod(ymaj, 1), 0):
                    ymaj = np.int(ymaj)
                text = self.ax.text(-labelpad+self.x_range[0],ymaj,str(ymaj).rjust(4), va='center', ha='right', fontsize=fsize)
                self.p_yticks.append(text)
                line = mpl.lines.Line2D([-ticklen+self.x_range[0],self.x_range[0]],[ymaj, ymaj], color='k')
                line.set_clip_on(False)
                self.ax.add_line(line)
                self.p_yticks.append(line)
            self.ygrid('update')

    def cartticks(self, s, *args, **kwargs):
        """ turns cartesian ticks on/off (xticks, yticks)

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """
        self.yticks(s)
        self.xticks(s)

    def polticks(self, s, *args, **kwargs):
        """ turns polar ticks on/off (lon, lon2)

        Parameters
        ----------
        s : boolean, string
            True or False, 'on' or 'off'

        Returns
        ----------
        None

        """

        fsize = kwargs.pop('fsize',"2.0%")
        fsize = self.get_fontsize(fsize)[0]
        font = fm.FontProperties()
        font.set_size(fsize)

        if s == 'on' or s == True:
            if self.float_axis:
                self.ax.axis["lon"].set_visible(True)
                self.ax.axis["lon"].major_ticklabels.set_visible(True)
                self.ax.axis["lon"].major_ticks.set_ticksize(5)
                self.ax.axis["lon"].invert_ticklabel_direction()
                self.ax.axis["lon"].major_ticklabels.set_fontproperties(font)

            #if self.ind == "PPI":
            self.ax.axis["lon2"].major_ticklabels.set_visible(True)
            self.ax.axis["lon2"].major_ticks.set_ticksize(5)
            self.ax.axis["lon2"].invert_ticklabel_direction()
            self.ax.axis["lon2"].major_ticklabels.set_fontproperties(font)

            if abs(self.x_range[0]) < self.radial_range[1]:
                left = True
                vert1 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.x_range[0],2)))+abs(self.y_range[0]))/self.yd
                vert2 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.x_range[0],2)))+abs(self.y_range[1]))/self.yd
                path = self.ax.axis["left"].line.get_path()
                vert = path.vertices
                vert[0][1] = 0 if vert2 > 1 else 1 - vert2
                vert[1][1] = 1 if vert1 > 1 else vert1
                self.ax.axis["left"].line.set_path(matplotlib.path.Path(vert))

            else:
                left =False

            if abs(self.x_range[1]) < abs(self.radial_range[1]):
                right = True
                vert1 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.x_range[1],2))) + abs(self.y_range[0]))/self.yd
                vert2 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.x_range[1],2))) + abs(self.y_range[1]))/self.yd
                path = self.ax.axis["right"].line.get_path()
                vert = path.vertices
                vert[1][1] = 1 if vert1 > 1 else vert1
                vert[0][1] = 0 if vert2 > 1 else 1 - vert2
                self.ax.axis["right"].line.set_path(matplotlib.path.Path(vert))

            else:
                right = False

            if abs(self.y_range[0]) < abs(self.radial_range[1]):
                bottom = True
                vert1 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.y_range[0],2)))+abs(self.x_range[0]))/self.xd
                vert2 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.y_range[0],2)))+abs(self.x_range[1]))/self.xd
                path = self.ax.axis["bottom"].line.get_path()
                vert = path.vertices
                vert[1][0] = 1 if vert1 > 1 else vert1
                vert[0][0] = 0 if vert2 > 1 else 1 - vert2
                self.ax.axis["bottom"].line.set_path(matplotlib.path.Path(vert))

            else:
                bottom =False

            if abs(self.y_range[1]) < abs(self.radial_range[1]):
                top = True
                vert1 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.y_range[1],2)))+abs(self.x_range[0]))/self.xd
                vert2 = (math.sqrt(abs(pow(self.radial_range[1],2) - pow(self.y_range[1],2)))+abs(self.x_range[1]))/self.xd
                path = self.ax.axis["top"].line.get_path()
                vert = path.vertices
                vert[0][0] = 0 if vert2 > 1 else 1 - vert2
                vert[1][0] = 1 if vert1 > 1 else vert1
                self.ax.axis["top"].line.set_path(matplotlib.path.Path(vert))
            else:
                top = False

            self.ax.axis["top"].major_ticklabels.set_fontproperties(font)
            self.ax.axis["bottom"].major_ticklabels.set_fontproperties(font)
            self.ax.axis["right"].major_ticklabels.set_fontproperties(font)
            self.ax.axis["left"].major_ticklabels.set_fontproperties(font)


            self.ax.axis["left"].set_visible(left)
            self.ax.axis["right"].set_visible(right)
            self.ax.axis["bottom"].set_visible(bottom)
            self.ax.axis["top"].set_visible(top)
            # make ticklabels of left and bottom axis visible.
            self.ax.axis["left"].major_ticklabels.set_visible(left)
            self.ax.axis["bottom"].major_ticklabels.set_visible(bottom)
            # but set tickmarklength to zero for better presentation
            self.ax.axis["left"].major_ticks.set_ticksize(5)
            self.ax.axis["bottom"].major_ticks.set_ticksize(5)
            # let right and top axis shows ticklabels for 1st coordinate (angle)
            self.ax.axis["left"].get_helper().nth_coord_ticks=0
            self.ax.axis["bottom"].get_helper().nth_coord_ticks=0

            # make ticklabels of right and top axis visible.
            self.ax.axis["right"].major_ticklabels.set_visible(right)
            self.ax.axis["top"].major_ticklabels.set_visible(top)
            # but set tickmarklength to zero for better presentation
            self.ax.axis["right"].major_ticks.set_ticksize(5)
            self.ax.axis["top"].major_ticks.set_ticksize(5)
            # let right and top axis shows ticklabels for 1st coordinate (angle)
            self.ax.axis["right"].get_helper().nth_coord_ticks=0
            self.ax.axis["top"].get_helper().nth_coord_ticks=0

        elif s == 'off' or s == False:
            if self.float_axis:
                self.ax.axis["lon"].major_ticklabels.set_visible(False)
                self.ax.axis["lon"].major_ticks.set_ticksize(0)
            #if self.ind == "PPI":
            self.ax.axis["lon2"].major_ticklabels.set_visible(False)
            self.ax.axis["lon2"].major_ticks.set_ticksize(0)

    def cartgrid(self,s, *args, **kwargs):
        """ turns cartesian grid/axis on/off (x, y)

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """
        self.ax.axis["right"].set_visible(s)
        self.ax.axis["bottom"].set_visible(s)
        self.ax.axis["left"].set_visible(s)
        self.ax.axis["top"].set_visible(s)
        self.xgrid(s)
        self.ygrid(s)

    def polgrid(self,s, *args, **kwargs):
        """ turns polar grid on/off

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """
        if s == 'on' or s == True:
            self.ax.grid(True)
        elif s == 'off' or s == False:
            self.ax.grid(False)

    def xgrid(self, s, *args, **kwargs):
        """ turns xgrid on/off

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """
        if s == 'on' or s == True:
            if hasattr(self, 'p_xgrid'):
                if self.p_xgrid:
                    for item in self.p_xgrid:
                        item.remove()
            self.p_xgrid = []
            for xmaj in self.rad:
                line = self.ax.axvline(x=xmaj,color='k', ls=':')
                self.p_xgrid.append(line)
        elif s == 'off' or s == False:
            if hasattr(self, 'p_xgrid'):
                if self.p_xgrid:
                    for item in self.p_xgrid:
                        item.remove()
                self.p_xgrid = None
                #self.remove(p_xgrid)
        elif s == 'update':
            self.xgrid('on')
        else:
            self.xgrid('on')
            self.xgrid('off')


    def ygrid(self, s, *args, **kwargs):
        """ turns xgrid on/off

        Parameters
        ----------
        s : boolean
            True or False

        Returns
        ----------
        None

        """
        if s == 'on' or s == True:
            if hasattr(self, 'p_ygrid'):
                if self.p_ygrid:
                    for item in self.p_ygrid:
                        item.remove()
            self.p_ygrid = []
            for ymaj in self.hgt:
                line = self.ax.axhline(y=ymaj,color='k', ls=':')
                self.p_ygrid.append(line)
        elif s == 'off' or s == False:
            if hasattr(self, 'p_ygrid'):
                if self.p_ygrid:
                    for item in self.p_ygrid:
                        item.remove()
                self.p_ygrid = None
        elif s == 'update':
            self.ygrid('on')
        else:
            self.ygrid('on')
            self.ygrid('off')

    def get_ypadding(self, pad, ax, *args, **kwargs):
        """ calculates labelpadding in direction of y-axis (e.g. x-label)

        Parameters
        ----------
        pad : string
                padding in percent of ax
        ax : relevant axis


        Returns
        ----------
        padding in axis values

        """

        if not isinstance(pad, Size._Base):
                padding = Size.from_any(pad,
                                    fraction_ref=Size.AxesY(ax))


        p = (self.xd/self.yd) / self.aspect
        return padding.get_size(ax)[0]*p

    def get_xpadding(self, pad, ax, *args, **kwargs):
        """ calculates labelpadding in direction of x-axis (e.g. y-label)

        Parameters
        ----------
        pad : string
                padding in percent of ax
        ax : relevant axis

        Returns
        ----------
        padding in axis values

        """
        if not isinstance(pad, Size._Base):
                padding = Size.from_any(pad,
                                    fraction_ref=Size.AxesX(ax))
        p = (self.yd/self.xd) * self.aspect
        return padding.get_size(ax)[0]

    def title(self, s, *args, **kwargs):
        """ plots figure title

        Parameters
        ----------
        s : string
                Title String

        Keyword args
        ----------
        fsize : fontsize in percent of axis size
        pad : string
                padding in percent of axis size

        Returns
        ----------
        None

        """
        fsize = kwargs.pop('fsize',"2%")
        pad = kwargs.pop('pad',"2%")
        labelpad = self.get_ypadding(pad=pad, ax = self.ax)
        fsize = self.get_fontsize(fsize)[0]

        if hasattr(self, 'p_title'):
            if self.p_title:
                self.p_title.remove()

        self.p_title = self.ax.text(self.x_range[0],labelpad + self.y_range[1],s, fontsize = fsize, va='center', ha='left')

    def x_title(self, s, *args, **kwargs):
        """ plots x axis title

        Parameters
        ----------
        s : string
                Title String

        Keyword args
        ----------
        fsize : fontsize in percent of axis size
        pad : string
                padding in percent of axis size

        Returns
        ----------
        None

        """
        fsize = kwargs.pop('fsize',"2%")
        pad = kwargs.pop('pad',"2%")

        if hasattr(self, 'p_xtitle'):
            if self.p_xtitle:
                self.p_xtitle.remove()

        labelpad = self.get_ypadding(pad=pad, ax = self.ax)
        fsize = self.get_fontsize(fsize)[0]

        self.p_xtitle = self.ax.text(self.xd/2.+self.x_range[0],-labelpad+self.y_range[0],s, fontsize = fsize, va='center', ha='center')

    def y_title(self, s, *args, **kwargs):
        """ plots y axis title

        Parameters
        ----------
        s : string
                Title String

        Keyword args
        ----------
        fsize : fontsize in percent of axis size
        pad : string
                padding in percent of axis size

        Returns
        ----------
        None

        """
        fsize = kwargs.pop('fsize',"2%")
        pad = kwargs.pop('pad',"2%")

        if hasattr(self, 'p_ytitle'):
            if self.p_ytitle:
                self.p_ytitle.remove()

        labelpad = self.get_xpadding(pad=pad, ax = self.ax)
        fsize = self.get_fontsize(fsize)[0]

        self.p_ytitle = self.ax.text(-labelpad + self.x_range[0],self.yd/2.+ self.y_range[0],s, fontsize = fsize, va='center', ha='left', rotation='vertical')

    def z_title(self, s, *args, **kwargs):
        """ plots colorbar title if colorbar is defined

        Returns
        ----------
        None

        """

        fsize = kwargs.pop('fsize',"2%")
        pad = kwargs.pop('pad',"2%")

        labelpad = self.get_xpadding(pad=pad, ax = self.ax)
        fsize = self.get_fontsize(fsize)[0]

        if hasattr(self, 'cbar'):
            self.cbar.set_label(s, size = fsize, *args, **kwargs)

    def copy_right(self, *args, **kwargs):
        """ plot copyright in lower left corner
            check position, its in plot coordinates not figure coordinates

        Keyword args
        ----------
        fsize : fontsize in percent of axis size
        text : string
                Copyright String
        padx : string
                padding in percent of axis size
        pady : string
                padding in percent of axis size

        Returns
        ----------
        None
        """

        fsize = kwargs.pop('fsize',"1%")
        text = kwargs.pop('text',r"""$\copyright\/2013\/ created with WRADLIB$""")
        padx = kwargs.pop('padx',"2%")
        pady = kwargs.pop('pady',"2%")

        padx = self.get_xpadding(padx,self.ax)
        pady = self.get_ypadding(pady,self.ax)
        fsize = self.get_fontsize(fsize)[0]

        if hasattr(self, 'p_copy'):
            if self.p_copy:
                self.p_copy.remove()

        self.p_copy = self.ax.text(self.x_range[0]- padx, - pady + self.y_range[0],text,fontsize=fsize, va='center', ha='left')

    def colorbar(self, *args, **kwargs):
        """ plot colorbar, vertical, right side

        Keyword args
        ----------
        vmin : plot minimum
        vmax : plot maximum
        z_res : colorbar tick resolution
        z_unit : string
                unit
        cbp : string
               padding in percent of axis size
        cbw : string
                width in percent of axis size

        Returns
        ----------
        cbar : colorbar object
        """

        key = ['vmin', 'vmax', 'z_res', 'ztitle', 'zunit']
        key1 = ['cbp', 'fsize', 'cbw']

        if kwargs:
            for k in key:
                if k in kwargs:
                    setattr(self, k, np.array(kwargs[k]))
                    kwargs.pop(k)
            for k in key1:
                if k in kwargs:
                    setattr(self, k, kwargs[k])
                    kwargs.pop(k)

        # get axis, create and add colorbar-cax,
        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes("right", size="0%", axes_class=mpl.axes.Axes)
        cbp = Size.from_any(self.cbp, fraction_ref=Size.Fraction(1/self.aspect, Size.AxesX(self.ax)))
        cbw = Size.from_any(self.cbw, fraction_ref=Size.Fraction(1/self.aspect, Size.AxesX(self.ax)))

        h = [# main axes
             Size.Fraction(1/self.aspect, Size.AxesX(self.ax)),
             cbp,
             cbw,
             ]

        v = [Size.AxesY(self.ax)]

        divider.set_horizontal(h)
        divider.set_vertical(v)

        self.ax.set_axes_locator(divider.new_locator(nx=0, ny=0))
        cax.set_axes_locator(divider.new_locator(nx=2, ny=0))

        self.fig.add_axes(cax)

        # set z_range and plot-clims
        self.z_range = [self.vmin,self.vmax]
        args[0].set_clim(vmin=self.vmin, vmax=self.vmax)

        # get ticks
        z_ticks = get_tick_vector(self.z_range,self.z_res)

        # plot colorbar
        if kwargs:
            if 'ticks' in kwargs:
                self.cbar = self.fig.colorbar(*args, cax=cax, **kwargs)
                z_ticks = kwargs['ticks']
            else:
                self.cbar = self.fig.colorbar(*args, cax=cax, ticks=z_ticks, **kwargs)

        # set font and size
        fsize = self.get_fontsize(self.fsize)[0]
        font = fm.FontProperties()
        font.set_family('sans-serif')
        font.set_size(fsize)

        # plot colorbar title and ticks
        if self.ztitle:
            ztitle = str(self.ztitle)
            if self.zunit:
                ztitle = ztitle +' ('+ str(self.zunit) + ')'
            self.cbar.set_label(ztitle, fontsize=fsize)
        z_ticks1 = [str(np.int(i)) for i in z_ticks]
        self.cbar.ax.set_yticklabels(z_ticks1, fontsize=fsize)

        return self.cbar



def plot_scan_strategy(ranges, elevs, vert_res=500., maxalt=10000., radaralt=0., ax=None):
    """Plot the vertical scanning strategy

    Parameters
    ----------
    ranges : array of ranges
    elevs : array of elevation angles

    """
    # just a dummy
    az=np.array([90.])

    polc = util.meshgridN(ranges, az, elevs)

    # get mean height over radar
    lat, lon, alt = georef.polar2latlonalt(polc[0].ravel(), polc[1].ravel(), polc[2].ravel(), (14.910948,120.259666, radaralt))
    alt = alt.reshape(len(ranges), len(elevs))
    r = polc[0].reshape(len(ranges), len(elevs))

    if ax==None:
        returnax = False
        fig = pl.figure()
        ax = fig.add_subplot(111)
    else:
        returnax = True
    # actual plotting
    for y in np.arange(0,10000.,vert_res):
        ax.axhline(y=y, color="grey")
    for x in ranges:
        ax.axvline(x=x, color="grey")
    for i in range(len(elevs)):
        ax.plot(r[:,i].ravel(), alt[:,i].ravel(), lw=2, color="black")
    pl.ylim(ymax=maxalt)
    ax.tick_params(labelsize="large")
    pl.xlabel("Range (m)", size="large")
    pl.ylabel("Height over radar (m)", size="large")
    for i, elev in enumerate(elevs):
        x = r[:,i].ravel()[-1]+1500.
        y = alt[:,i].ravel()[-1]
        if  y > maxalt:
            ix = np.where(alt[:,i].ravel()<maxalt)[0][-1]
            x = r[:,i].ravel()[ix]
            y = maxalt+100.
        pl.text(x, y, str(elev), fontsize="large")

    if returnax:
        return ax
    pl.show()


def plot_plan_and_vert(x, y, z, dataxy, datazx, datazy, unit="", title="", saveto="", **kwargs):
    """Plot 2-D plan view of <dataxy> together with vertical sections <dataxz> and <datazy>

    Parameters
    ----------
    x : array of x-axis coordinates
    y : array of y-axis coordinates
    z : array of z-axis coordinates
    dataxy : 2d array of shape (len(x), len(y))
    datazx : 2d array of shape (len(z), len(x))
    datazy : 2d array of shape (len(z), len(y))
    unit : string (unit of data arrays)
    title: string
    saveto : file path if figure should be saved
    **kwargs : other kwargs which can be passed to pylab.contourf

    """

    fig = pl.figure(figsize=(10, 10))

    # define axes
    left, bottom, width, height = 0.1, 0.1, 0.6, 0.2
    ax_xy = pl.axes((left, bottom, width, width))
    ax_x  = pl.axes((left, bottom+width, width, height))
    ax_y  = pl.axes((left+width, bottom, height, width))
    ax_cb  = pl.axes((left+width+height+0.02, bottom, 0.02, width))

    # set axis label formatters
    ax_x.xaxis.set_major_formatter(NullFormatter())
    ax_y.yaxis.set_major_formatter(NullFormatter())

    # draw CAPPI
    pl.axes(ax_xy)
    xy = pl.contourf(x,y,dataxy, **kwargs)
    pl.grid(color="grey", lw=1.5)

    # draw colorbar
    cb = pl.colorbar(xy, cax=ax_cb)
    cb.set_label("(%s)" % unit)

    # draw upper vertical profil
    ax_x.contourf(x, z, datazx.transpose(), **kwargs)

    # draw right vertical profil
    ax_y.contourf(z, y, datazy, **kwargs)

    # label axes
    ax_xy.set_xlabel('x (km)')
    ax_xy.set_ylabel('y (km)')
    ax_x.set_xlabel('')
    ax_x.set_ylabel('z (km)')
    ax_y.set_ylabel('')
    ax_y.set_xlabel('z (km)')

    def xycoords(x,pos):
        'The two args are the value and tick position'
        return "%d" % (x/1000.)

    xyformatter = FuncFormatter(xycoords)

    def zcoords(x,pos):
        'The two args are the value and tick position'
        return ( "%.1f" % (x/1000.) ).rstrip('0').rstrip('.')

    zformatter = FuncFormatter(zcoords)

    ax_xy.xaxis.set_major_formatter(xyformatter)
    ax_xy.yaxis.set_major_formatter(xyformatter)
    ax_x.yaxis.set_major_formatter(zformatter)
    ax_y.xaxis.set_major_formatter(zformatter)

    if not title=="":
        # add a title - here, we have to create a new axes object which will be invisible
        # then the invisble axes will get a title
        tax = pl.axes((left, bottom+width+height+0.01, width+height, 0.01), frameon=False, axisbg="none")
        tax.get_xaxis().set_visible(False)
        tax.get_yaxis().set_visible(False)
        pl.title(title)
    if saveto=='':
        # show plot
        pl.show()
        if not pl.isinteractive():
            # close figure eplicitely if pylab is not in interactive mode
            pl.close()
    else:
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()


def plot_max_plan_and_vert(x, y, z, data, unit="", title="", saveto="", **kwargs):
    """Plot according to <plot_plan_and_vert> with the maximum values along the three axes of <data>
    """
    plot_plan_and_vert(x, y, z, np.max(data,axis=2), np.max(data, axis=0), np.max(data, axis=1), unit, title, saveto, **kwargs)


def plot_tseries(dtimes, data, ax=None, labels=None, datefmt='%b %d, %H:%M', colors=None, ylabel="", title="", fontsize="medium", saveto="", **kwargs):
    """Plot time series data (e.g. gage recordings)

    Parameters
    ----------
    dtimes : array of datetime objects (time steps)
    data : 2D array of shape ( num time steps, num data series )
    labels : list of strings (names of data series)
    title : string
    kwargs : keyword arguments related to pylab.plot

    """
    if ax==None:
        returnax = False
        fig = pl.figure()
        ax  = fig.add_subplot(1,1,1,  title=title)
    else:
        returnax = True
##    if labels==None:
##        labels = ["series%d"%i for i in range(1, data.shape[1]+1)]
##    for i, label in enumerate(labels):
##        ax.plot_date(mpl.dates.date2num(dtimes),data[:,i],label=label, color=colors[i], **kwargs)
    ax.plot_date(mpl.dates.date2num(dtimes), data, **kwargs)
    ax.xaxis.set_major_formatter(mdates.DateFormatter(datefmt))
    pl.setp(ax.get_xticklabels(), visible=True)
    pl.setp(ax.get_xticklabels(), rotation=-30, horizontalalignment='left')
    ax.set_ylabel(ylabel, size=fontsize)
    ax = set_ticklabel_size(ax,fontsize)
    ax.legend(loc='best')

    if returnax:
        return ax

    if saveto=="":
        # show plot
        pl.show()
        if not pl.isinteractive():
            # close figure eplicitely if pylab is not in interactive mode
            pl.close()
    else:
        # save plot to file
        if ( path.exists(path.dirname(saveto)) ) or ( path.dirname(saveto)=='' ):
            pl.savefig(saveto)
            pl.close()

def set_ticklabel_size(ax, size):
    """
    """
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(size)
    return ax

if __name__ == '__main__':
    print 'wradlib: Calling module <vis> as main...'



