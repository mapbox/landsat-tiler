
SHELL = /bin/bash

all: build package

build:
	docker build --tag lambda:latest .

#Local Test
test:
	docker run \
		-w /var/task/ \
		--name lambda \
		--env AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID} \
		--env AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY} \
 		--env AWS_REGION=us-west-2 \
		--env PYTHONPATH=/var/task \
		--env GDAL_CACHEMAX=75% \
		--env GDAL_DISABLE_READDIR_ON_OPEN=TRUE \
		--env GDAL_TIFF_OVR_BLOCKSIZE=512 \
		--env VSI_CACHE=TRUE \
		--env VSI_CACHE_SIZE=536870912 \
		-itd \
		lambda:latest
	docker cp package.zip lambda:/tmp/package.zip
	docker exec -it lambda bash -c 'unzip -q /tmp/package.zip -d /var/task/'
	docker exec -it lambda bash -c 'pip3 install boto3 jmespath python-dateutil -t /var/task'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/bounds/LC80230312016320LGN00", "queryStringParameters": "null", "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/metadata/LC80230312016320LGN00", "queryStringParameters": {"pmin":"2", "pmax":"99.8"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/processing/LC80230312016320LGN00/8/65/94.png", "queryStringParameters": {"ratio":"(b5-b4)/(b5+b4)"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/tiles/LC80230312016320LGN00/8/65/94.png", "queryStringParameters": {"rgb":"11", "histo":"0,1000"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/tiles/LC80230312016320LGN00/8/65/94.png", "queryStringParameters": {"rgb":"5,3,2", "histo":"722,5088;859,4861;1164,5204"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker exec -it lambda python3 -c 'from app.landsat import APP; print(APP({"path": "/landsat/tiles/LC80230312016320LGN00/8/65/94.png", "queryStringParameters": {"rgb":"4,3,2", "histo":"722,5088;859,4861;1164,5204", "pan":"true"}, "pathParameters": "null", "requestContext": "null", "httpMethod": "GET"}, None))'
	docker stop lambda
	docker rm lambda


package:
	docker run \
		-w /var/task/ \
		--name lambda \
		-itd \
		lambda:latest
	docker cp lambda:/tmp/package.zip package.zip
	docker stop lambda
	docker rm lambda

shell:
	docker run \
		--name lambda  \
		--volume $(shell pwd)/:/data \
		--env PYTHONPATH=/var/task/vendored \
		--env GDAL_CACHEMAX=75% \
		--env GDAL_DISABLE_READDIR_ON_OPEN=TRUE \
		--env GDAL_TIFF_OVR_BLOCKSIZE=512 \
		--env VSI_CACHE=TRUE \
		--env VSI_CACHE_SIZE=536870912 \
		--rm \
		-it \
		lambda:latest /bin/bash

deploy:
	sls deploy

clean:
	docker stop lambda
	docker rm lambda
