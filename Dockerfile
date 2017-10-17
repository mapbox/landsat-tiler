# Use the official amazonlinux AMI image with GDAL from RemotePixel
FROM remotepixel/amazonlinux-gdal:latest

# Install Python dependencies
RUN pip3 install rio-tiler==0.0.2 --no-binary numpy,rasterio -t /tmp/vendored -U

COPY app /tmp/vendored/app

# Reduce Lambda package size to fit the 250Mb limit
RUN find /tmp/vendored \( -type d -a -name test -o -name tests \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -print0 | xargs -0 rm -f

# Create archive
RUN cd /tmp && zip -r9q /tmp/package.zip vendored/*

RUN cd $APP_DIR/local && zip -r9q --symlinks /tmp/package.zip lib/*.so*
RUN cd $APP_DIR/local && zip -r9q /tmp/package.zip share

# Cleanup
RUN rm -rf /tmp/vendored/
