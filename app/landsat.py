"""app.landsat: handle request for Landsat-tiler"""

import json

from cachetools.func import rr_cache

from rio_tiler import landsat8
from rio_tiler.utils import array_to_img

from app.proxy import API

LANDSAT_APP = API(app_name="landsat-tiler")


@rr_cache()
@LANDSAT_APP.route('/landsat/bounds/<scene>', methods=['GET'], cors=True)
def landsat_bounds(scene):
    """
    Handle bounds requests
    """
    info = landsat8.bounds(scene)
    return ('OK', 'application/json', json.dumps(info))


@rr_cache()
@LANDSAT_APP.route('/landsat/metadata/<scene>', methods=['GET'], cors=True)
def landsat_metadata(scene):
    """
    Handle metadata requests
    """
    query_args = LANDSAT_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    pmin = query_args.get('pmin', 2)
    pmin = float(pmin) if isinstance(pmin, str) else pmin

    pmax = query_args.get('pmax', 98)
    pmax = float(pmax) if isinstance(pmax, str) else pmax

    info = landsat8.metadata(scene, pmin, pmax)
    return ('OK', 'application/json', json.dumps(info))


@rr_cache()
@LANDSAT_APP.route('/landsat/tiles/<scene>/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def landsat_tile(scene, tile_z, tile_x, tile_y, tileformat):
    """
    Handle tile requests
    """
    query_args = LANDSAT_APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    rgb = query_args.get('rgb', '4,3,2')
    rgb = map(int, rgb.split(',')) if isinstance(rgb, str) else rgb
    rgb = tuple(rgb)

    r_bds = query_args.get('r_bds', '0,16000')
    if isinstance(r_bds, str):
        r_bds = map(int, r_bds.split(','))
    r_bds = tuple(r_bds)

    g_bds = query_args.get('g_bds', '0,16000')
    if isinstance(g_bds, str):
        g_bds = map(int, g_bds.split(','))
    g_bds = tuple(g_bds)

    b_bds = query_args.get('b_bds', '0,16000')
    if isinstance(b_bds, str):
        b_bds = map(int, b_bds.split(','))
    b_bds = tuple(b_bds)

    tilesize = query_args.get('tile', 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    pan = True if query_args.get('pan') else False

    tile = landsat8.tile(scene, tile_x, tile_y, tile_z, rgb, r_bds, g_bds,
                         b_bds, pan=pan, tilesize=tilesize)

    tile = array_to_img(tile, tileformat)

    return ('OK', f'image/{tileformat}', tile)


@LANDSAT_APP.route('/favicon.ico', methods=['GET'], cors=True)
def favicon():
    """
    favicon
    """
    return('NOK', 'text/plain', '')
