'use strict';

mapboxgl.accessToken = '{YOUR-MAPBOX-TOKEN}';
const landsat_tiler_url = '{YOUR-API-GATEWAY-ENDPOINT}'; //e.g https://xxxxxxxxxx.execute-api.xxxxxxx.amazonaws.com/production
const sat_api = 'https://api.developmentseed.org/satellites/?search=';

let scope = {};

const sortScenes = (a, b) => {
    return Date.parse(b.date) - Date.parse(a.date);
};


const parseSceneid_c1 = (sceneid) => {

    const sceneid_info = sceneid.split('_');

    return {
        satellite: sceneid_info[0].slice(0,1) + sceneid_info[0].slice(3),
        sensor:  sceneid_info[0].slice(1,2),
        correction_level: sceneid_info[1],
        path: sceneid_info[2].slice(0,3),
        row: sceneid_info[2].slice(3),
        acquisition_date: sceneid_info[3],
        ingestion_date: sceneid_info[4],
        collection: sceneid_info[5],
        category: sceneid_info[6]
    };
};


const parseSceneid_pre = (sceneid) => {

    return {
        sensor:  sceneid.slice(1,2),
        satellite: sceneid.slice(2,3),
        path: sceneid.slice(3,6),
        row: sceneid.slice(6,9),
        acquisitionYear: sceneid.slice(9,13),
        acquisitionJulianDay: sceneid.slice(13,16),
        groundStationIdentifier: sceneid.slice(16,19),
        archiveVersion: sceneid.slice(19,21)
    };
};


const buildQueryAndRequestL8 = (features) => {
    $('.list-img').scrollTop(0);
    $('.list-img').empty();
    $('.errorMessage').addClass('none');
    $('.landsat-info').addClass('none');

    if (map.getSource('landsat-tiles')) map.removeSource('landsat-tiles');
    if (map.getLayer('landsat-tiles')) map.removeLayer('landsat-tiles');

    const prStr = [].concat.apply([], features.map(function(e){
        return '(path:' + e.properties.PATH.toString() + '+AND+row:' + e.properties.ROW.toString() + ')';
    })).join('+OR+');

    const query = `${sat_api}satellite_name:landsat-8+AND+(${prStr})&limit=2000`;
    const results = [];

    $.getJSON(query, (data) => {
        if (data.meta.found !== 0) {

            for (let i = 0; i < data.results.length; i += 1) {
                let scene = {};
                scene.path = data.results[i].path.toString();
                scene.row = data.results[i].row.toString();
                scene.grid = data.results[i].path + '/' + data.results[i].row;
                scene.date = data.results[i].date;
                scene.cloud = data.results[i].cloud_coverage;
                scene.browseURL = data.results[i].browseURL.replace('http://', 'https://');
                scene.thumbURL = scene.browseURL.replace('browse/', 'browse/thumbnails/')
                scene.sceneID = data.results[i].scene_id;
                scene.awsID = (Date.parse(scene.date) < Date.parse('2017-05-01')) ?  data.results[i].scene_id.replace(/LGN0[0-9]/, 'LGN00') : data.results[i].LANDSAT_PRODUCT_ID;
                results.push(scene);
            }

            results.sort(sortScenes);

          for (let i = 0; i < results.length; i += 1) {

              $('.list-img').append(
                  '<div class="list-element" onclick="initScene(\'' + results[i].awsID + '\',\'' + results[i].date + '\')">' +
                        '<div class="block-info">' +
                            '<img "class="img-item lazy lazyload" src="' + results[i].thumbURL + '">' +
                        '</div>' +
                        '<div class="block-info">' +
                            '<span class="scene-info">' + results[i].sceneID + '</span>' +
                            '<span class="scene-info"><svg class="icon inline-block"><use xlink:href="#icon-clock"/></svg> ' + results[i].date + '</span>' +
                        '</div>' +
                    '</div>');
          }

      } else {
          $('.errorMessage').removeClass('none');
      }
    })
    .always(() => {
        $('.spin').addClass('none');
    })
    .fail(() => {
        $('.errorMessage').removeClass('none');
    });
}

const initScene = (sceneID, sceneDate) => {
    $('.metaloader').removeClass('none');
    $('.errorMessage').addClass('none');

    let min = $("#minCount").val();
    let max = $("#maxCount").val();
    const query = `${landsat_tiler_url}/landsat/metadata/${sceneID}?'pmim=${min}&pmax=${max}`;

    $.getJSON(query, (data) => {
        scope.imgMetadata = data;
        updateRasterTile();
        $('.landsat-info').removeClass('none');
        $('.landsat-info .l8id').text(sceneID);
        $('.landsat-info .l8date').text(sceneDate);
    })
        .fail(() => {
            if (map.getSource('landsat-tiles')) map.removeSource('landsat-tiles');
            if (map.getLayer('landsat-tiles')) map.removeLayer('landsat-tiles');
            $('.landsat-info span').text('');
            $('.landsat-info').addClass('none');
            $('.errorMessage').removeClass('none');
        })
        .always(() => {
            $('.metaloader').addClass('none');
        });
};


const updateRasterTile = () => {
    if (map.getSource('landsat-tiles')) map.removeSource('landsat-tiles');
    if (map.getLayer('landsat-tiles')) map.removeLayer('landsat-tiles');

    let meta = scope.imgMetadata;

    let rgb = $(".img-display-options .toggle-group input:checked").attr("data");
    const bands = rgb.split(',');

    // NOTE: Calling 512x512px tiles is a bit longer but gives a
    // better quality image and reduce the number of tiles requested

    // HACK: Trade-off between quality and speed. Setting source.tileSize to 512 and telling landsat-tiler
    // to get 256x256px reduces the number of lambda calls (but they are faster)
    // and reduce the quality because MapboxGl will oversample the tile.

    const tileURL = `${landsat_tiler_url}/landsat/tiles/${meta.sceneid}/{z}/{x}/{y}.png?` +
        `rgb=${rgb}` +
        '&tile=256' +
        `&histo=${meta.rgbMinMax[bands[0]]}-${meta.rgbMinMax[bands[1]]}-${meta.rgbMinMax[bands[2]]}`;

    const attrib = '<a href="https://landsat.usgs.gov/landsat-8"> &copy; USGS/NASA Landsat</a>';

    $('.landsat-info .l8rgb').text(rgb);

    map.addSource('landsat-tiles', {
        type: 'raster',
        tiles: [tileURL],
        attribution : attrib,
        bounds: scope.imgMetadata.bounds,
        minzoom: 7,
        maxzoom: 14,
        tileSize: 256
    });

    map.addLayer({
        'id': 'landsat-tiles',
        'type': 'raster',
        'source': 'landsat-tiles'
    });
};


const updateMetadata = () => {
    if (!map.getSource('landsat-tiles')) return;
    initScene(scope.imgMetadata.sceneid, scope.imgMetadata.date);
}


$(".img-display-options .toggle-group").change(() => {
    if (map.getSource('landsat-tiles')) updateRasterTile();
});

document.getElementById("btn-clear").onclick = () => {
  if (map.getLayer('landsat-tiles')) map.removeLayer('landsat-tiles');
  if (map.getSource('landsat-tiles')) map.removeSource('landsat-tiles');
  map.setFilter("L8_Highlighted", ["in", "PATH", ""]);
  map.setFilter("L8_Selected", ["in", "PATH", ""]);

  $('.list-img').scrollLeft(0);
  $('.list-img').empty();

  $(".metaloader").addClass('off');
  $('.errorMessage').addClass('none');
  $(".landsat-info span").text('');
  $(".landsat-info").addClass('none');

  scope = {};

  $("#minCount").val(5);
  $("#maxCount").val(95);

  $(".img-display-options .toggle-group input").prop('checked', false);
  $(".img-display-options .toggle-group input[data='4,3,2']").prop('checked', true);

  $('.map').removeClass('in');
  $('.right-panel').removeClass('in');
  map.resize();
};

////////////////////////////////////////////////////////////////////////////////

var map = new mapboxgl.Map({
    container: 'map',
    style: 'mapbox://styles/vincentsarago/ciy1m6t8y005a2rr09jhfplg3',
    center: [-70.50, 40],
    zoom: 3,
    attributionControl: true,
    minZoom: 3,
    maxZoom: 14
});

map.addControl(new mapboxgl.NavigationControl(), 'top-right');

map.on('mousemove', (e) => {
    const features = map.queryRenderedFeatures(e.point, {layers: ['landsat8-pathrow']});

    let pr = ['in', 'PATH', ''];

    if (features.length !== 0) {
        pr =  [].concat.apply([], ['any', features.map(e => {
            return ['all', ['==', 'PATH', e.properties.PATH], ['==', 'ROW', e.properties.ROW]];
        })]);
    }
    map.setFilter('L8_Highlighted', pr);
});

map.on('click', (e) => {
    $('.right-panel').addClass('in');
    $('.spin').removeClass('none');
    const features = map.queryRenderedFeatures(e.point, {layers: ['landsat8-pathrow']});

    if (features.length !== 0) {
        $('.map').addClass('in');
        $('.list-img').removeClass('none');
        map.resize();

        const pr =  [].concat.apply([], ['any', features.map(e => {
            return ['all', ['==', 'PATH', e.properties.PATH], ['==', 'ROW', e.properties.ROW]];
        })]);

        map.setFilter('L8_Selected', pr);

        buildQueryAndRequestL8(features);

        const geojson = {
          'type': 'FeatureCollection',
          'features': features
        };

        const extent = turf.bbox(geojson);
        const llb = mapboxgl.LngLatBounds.convert([[extent[0], extent[1]], [extent[2], extent[3]]]);
        map.fitBounds(llb, {padding: 50});

    } else {
        $('.spin').addClass('none');
        map.setFilter('L8_Selected', ['in', 'PATH', '']);
    }
});

map.on('load', () => {
    map.addSource('landsat', {
        'type': 'vector',
        'url': 'mapbox://vincentsarago.8ib6ynrs'
    });

    map.addLayer({
        'id': 'L8_Highlighted',
        'type': 'fill',
        'source': 'landsat',
        'source-layer': 'Landsat8_Desc_filtr2',
        'paint': {
            'fill-outline-color': '#1386af',
            'fill-color': '#0f6d8e',
            'fill-opacity': 0.3
        },
        'filter': ['in', 'PATH', '']
    });

    map.addLayer({
        'id': 'L8_Selected',
        'type': 'line',
        'source': 'landsat',
        'source-layer': 'Landsat8_Desc_filtr2',
        'paint': {
            'line-color': '#000',
            'line-width': 1
        },
        'filter': ['in', 'PATH', '']
    });

    $('.loading-map').addClass('off');
});
