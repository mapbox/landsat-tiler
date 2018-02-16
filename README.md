# landsat-tiler

#### AWS Lambda + Landsat AWS PDS = landsat-tiler

### Description

Create a highly customizable `serverless` tile server for Amazon's Landsat Public Dataset.
This project is based on [rio-tiler](https://github.com/mapbox/rio-tiler) python library.

![landsat-tiler-small](https://cloud.githubusercontent.com/assets/10407788/22255896/ec49f448-e226-11e6-8798-82794174eafe.gif)


#### Landsat data on AWS

Since 2015 Landsat 8 data is hosted on AWS and can be freely accessed. This dataset is growing over 700 scenes a day and have archive up to 2013.

> AWS has made Landsat 8 data freely available on Amazon S3 so that anyone can use our on-demand computing resources to perform analysis and create new products without needing to worry about the cost of storing Landsat data or the time required to download it.

more info: https://aws.amazon.com/public-datasets/landsat/

Something important about AWS Landsat-pds is that each Landsat scene has its individual bands stored as [cloud optimized GeoTIFF](https://trac.osgeo.org/gdal/wiki/CloudOptimizedGeoTIFF). While this is a critical point to work with the data, it also means that to create an RGB image and visualize it, you have to go through a lot of manual steps.

#### Lambda function

AWS Lambda is a service that lets you run functions in Node, Python, or Java in response to different triggers like API calls, file creation, database edits, etc.
In addition to only have to provide code, an other crucial point of AWS Lambda it that you only pay for the execution of the function, you don't have to pay for a 24/24h running server. It's called **serverless** cause you only need to care about the code you provide.

---

# Installation

##### Requirement
  - AWS Account
  - Docker
  - node + npm


#### Create the package

Creating a python lambda package with some C (or Cython) libraries like Rasterio/GDAL has never been an easy task because you have to compile and build it on the same infrastructure where it's going to be used (Amazon linux AMI). Until recently, to create your package you had to launch an EC2 instance using the official Amazon Linux AMI and create your package on it (see [perrygeo blog](http://www.perrygeo.com/running-python-with-compiled-code-on-aws-lambda.html) or [Remotepixel blog](https://remotepixel.ca/blog/landsat8-ndvi-20160212.html)).

But this was before, Late 2016, the AWS team released the Amazon Linux image on docker, so it's now possible to use it `locally` to compile C libraries and create complex lambda package ([see Dockerfile](https://github.com/mapbox/landsat-tiler/blob/master/Dockerfile)).

Note: to stay under AWS lambda package sizes limits (100Mb zipped file / 250Mb unzipped archive) we need to use some [`tricks`](https://github.com/mapbox/landsat-tiler/blob/e4eebb512f51c55d95607daa483a14d2091fa0a1/Dockerfile#L30).
- use Rasterio wheels which is a complete rasterio distribution that support GeoTIFF, OpenJPEG formats.
- remove every packages that are already available natively in AWS Lambda (boto3, botocore ...)
- keep only precompiled python code (`.pyc`) so it lighter and it loads faster

```bash
# Build Amazon linux AMI docker container + Install Python modules + create package
git clone https://github.com/mapbox/landsat-tiler.git
cd landsat-tiler/
make all
```

#### Deploy to AWS
One of the easiest way to **Build** and **Deploy** a Lambda function is to use [Serverless](https://serverless.com) toolkit. We took care of the `building` part with docker so we will just ask **Serverless** to *only* upload our package file to AWS S3, to setup AWS Lambda and AWS API Gateway.

```bash
#configure serverless (https://serverless.com/framework/docs/providers/aws/guide/credentials/)
npm install
sls deploy
```

<img width="500" alt="sls deploy" src="https://cloud.githubusercontent.com/assets/10407788/22188728/d9ffec44-e0e5-11e6-9a77-569a791ccaf2.png">

:tada: You should be all set there.

---
# Use it: Landsat-viewer

#### lambda-tiler + Mapbox GL + Satellite API

The `viewer/` directory contains a UI example to use with your new Lambda Landsat tiler endpoint. It combine the power of mapbox-gl and the nice developmentseed [sat-api](https://github.com/sat-utils/sat-api) to create a simple and fast **Landsat-viewer**.

To be able to run it, edit those [two lines](https://github.com/mapbox/landsat-tiler/blob/master/viewer/js/app.js#L3-L4) in `viewer/js/app.js`
```js
// viewer/js/app.js
3  mapboxgl.accessToken = '{YOUR-MAPBOX-TOKEN}';
4  const landsat_tiler_url = "{YOUR-API-GATEWAY-URL}";
```

## Workflow

1. One AWS λ call to get min/max percent cut value for all the bands and bounds

  *Path:* **/landsat/metdata/{landsat scene id}**

  *Inputs:*

  - sceneid: Landsat product id (or scene id for scene < 1st May 2017)

  *Options:*

  - pmin: Histogram cut minimum value in percent (default: 2)  
  - pmax: Histogram cut maximum value in percent (default: 98)  

  *Output:* (dict)

  - bounds: (minX, minY, maxX, maxY) (list)
  - sceneid: scene id (string)
  - rgbMinMax: Min/Max DN values for the linear rescaling (dict)

  *Example:* `<api-gateway-url>/landsat/metadata/LC08_L1TP_016037_20170813_20170814_01_RT?pmin=5&pmax=95`

2. Parallel AWS λ calls (one per mercator tile) to retrieve corresponding Landsat data

  *Path:* **/landsat/tiles/{landsat scene id}/{z}/{x}/{y}.{ext}**

  *Inputs:*

  - sceneid: Landsat product id (or scene id for scene < 1st May 2017)
  - x: Mercator tile X index
  - y: Mercator tile Y index
  - z: Mercator tile ZOOM level
  - ext: Image format to return ("jpg" or "png")

  *Options:*

  - rgb: Bands index for the RGB combination (default: (4, 3, 2))
  - histo: DN min and max values (default: (0, 16000))
  - tile: Output image size (default: 256)
  - pan: If True, apply pan-sharpening(default: False)

  *Output:*

  - base64 encoded image PNG or JPEG (string)

  *Example:*
  - `<api-gateway-url>/landsat/tile/LC08_L1TP_016037_20170813_20170814_01_RT/8/71/102.png`
  - `<api-gateway-url>/landsat/tile/LC08_L1TP_016037_20170813_20170814_01_RT/8/71/102.png?rgb=5,4,3&histo=100,3000-130,270-500,4500&tile=1024&pan=true`


---
#### Live Demo: https://viewer.remotepixel.ca

#### Infos & links
- [rio-tiler](https://github.com/mapbox/rio-tiler) rasterio plugin that process Landsat data hosted on AWS S3.
- [Introducing the AWS Lambda Tiler](https://hi.stamen.com/stamen-aws-lambda-tiler-blog-post-76fc1138a145)
- Humanitarian OpenStreetMap Team [oam-dynamic-tiler](https://github.com/hotosm/oam-dynamic-tiler)
- [Linux Amazon AMI container](http://docs.aws.amazon.com/AmazonECR/latest/userguide/amazon_linux_container_image.html)
