pip install virtualenv
sudo apt-get install python-dev
make make-env
source activate
pip install -r requirements.txt
./fix-path.sh
pip install git+https://github.com/pythonforfacebook/facebook-sdk.git
pip install git+https://github.com/geraldbaeck/Face-Recognition-Training-for-Sky-Biometry-API.git
