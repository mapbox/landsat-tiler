"""app.landsat: handle request for Landsat-tiler"""

import re
import json

import numpy as np

from rio_tiler import landsat8
from rio_tiler.utils import array_to_img, linear_rescale, get_colormap, expression, b64_encode_img

from aws_sat_api.search import landsat as landsat_search

from lambda_proxy.proxy import API

APP = API(app_name="landsat-tiler")


class LandsatTilerError(Exception):
    """Base exception class"""


@APP.route('/landsat/search', methods=['GET'], cors=True)
def search():
    """Handle search requests
    """
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    path = query_args['path']
    row = query_args['row']
    full = query_args.get('full', True)

    data = list(landsat_search(path, row, full))
    info = {
        'request': {'path': path, 'row': row, 'full': full},
        'meta': {'found': len(data)},
        'results': data}

    return ('OK', 'application/json', json.dumps(info))


@APP.route('/landsat/bounds/<scene>', methods=['GET'], cors=True)
def bounds(scene):
    """Handle bounds requests
    """
    info = landsat8.bounds(scene)
    return ('OK', 'application/json', json.dumps(info))


@APP.route('/landsat/metadata/<scene>', methods=['GET'], cors=True)
def metadata(scene):
    """Handle metadata requests
    """
    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    pmin = query_args.get('pmin', 2)
    pmin = float(pmin) if isinstance(pmin, str) else pmin

    pmax = query_args.get('pmax', 98)
    pmax = float(pmax) if isinstance(pmax, str) else pmax

    info = landsat8.metadata(scene, pmin, pmax)
    return ('OK', 'application/json', json.dumps(info))


@APP.route('/landsat/tiles/<scene>/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def tile(scene, tile_z, tile_x, tile_y, tileformat):
    """Handle tile requests
    """
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    bands = query_args.get('rgb', '4,3,2')
    bands = tuple(re.findall(r'\d+', bands))

    histoCut = query_args.get('histo', ';'.join(['0,16000'] * len(bands)))
    histoCut = re.findall(r'\d+,\d+', histoCut)
    histoCut = list(map(lambda x: list(map(int, x.split(','))), histoCut))

    if len(bands) != len(histoCut):
        raise LandsatTilerError('The number of bands doesn\'t match the number of histogramm values')

    tilesize = query_args.get('tile', 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    pan = True if query_args.get('pan') else False
    tile, mask = landsat8.tile(scene, tile_x, tile_y, tile_z, bands, pan=pan, tilesize=tilesize)

    rtile = np.zeros((len(bands), tilesize, tilesize), dtype=np.uint8)
    for bdx in range(len(bands)):
        rtile[bdx] = np.where(mask, linear_rescale(tile[bdx], in_range=histoCut[bdx], out_range=[0, 255]), 0)
    img = array_to_img(rtile, mask=mask)
    str_img = b64_encode_img(img, tileformat)
    return ('OK', f'image/{tileformat}', str_img)


@APP.route('/landsat/processing/<scene>/<int:z>/<int:x>/<int:y>.<ext>', methods=['GET'], cors=True)
def ratio(scene, tile_z, tile_x, tile_y, tileformat):
    """Handle processing requests
    """
    if tileformat == 'jpg':
        tileformat = 'jpeg'

    query_args = APP.current_request.query_params
    query_args = query_args if isinstance(query_args, dict) else {}

    ratio_value = query_args['ratio']
    APP.log.debug(f'{ratio_value}')

    range_value = query_args.get('range', [-1, 1])

    tilesize = query_args.get('tile', 256)
    tilesize = int(tilesize) if isinstance(tilesize, str) else tilesize

    tile, mask = expression(scene, tile_x, tile_y, tile_z, ratio_value, tilesize=tilesize)
    if len(tile.shape) == 2:
        tile = np.expand_dims(tile, axis=0)

    rtile = np.where(mask, linear_rescale(tile, in_range=range_value, out_range=[0, 255]), 0).astype(np.uint8)
    img = array_to_img(rtile, color_map=get_colormap(name='cfastie'), mask=mask)
    str_img = b64_encode_img(img, tileformat)
    return ('OK', f'image/{tileformat}', str_img)


@APP.route('/favicon.ico', methods=['GET'], cors=True)
def favicon():
    """favicon
    """
    return('NOK', 'text/plain', '')
