sudo apt-get update
sudo apt-get install libgdal-dev

which gdal-config
gdalc-config --version
pip3 install GDAL
#export PATH=$PATH:/path/to/gdal-config/directory
#export GDAL_CONFIG=/path/to/gdal-config
#export GDAL_VERSION=3.2.0  # インストールされているバージョンに合わせて変更してください


pip3 install -r requirements.txt
#python3 manage.py collectstatic
#python3 manage.py migrate
#python3 manage.py custom_createsuperuser