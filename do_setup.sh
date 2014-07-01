pip install virtualenv
sudo apt-get install python-dev
make make-env
source activate
pip install -r requirements.txt
./fix-path.sh
cd python-face-client
python setup.py install
