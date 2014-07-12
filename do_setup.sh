pip install virtualenv
sudo apt-get install python-dev
sudo apt-get install libjpeg-dev
make make-env
source activate
pip install -r requirements.txt
./fix-path.sh
cd python-face-client
python setup.py install
#pip install git+https://github.com/geraldbaeck/Face-Recognition-Training-for-Sky-Biometry-API.git
