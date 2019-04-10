### Some useful things to know.

#### Environment

Prepare a Python (3.6.5) virtualenv with the required dependencies:

```bash
virtualenv --python=/orange/ubrew/data/bin/python3.6 ~/python_envs/webapi_lecturemt
source ~/python_envs/webapi_lecturemt
pip install -r requirements.txt  
```

Special note: 

At the moment, the version of knmt in pip is too old.
So it's required to do that:

```bash
pip uninstall knmt
cd ~/knmt-latest
pip install -e .
```


#### Logging

```bash
cp conf/config_logging.ini.sample conf/config_logging.ini
mkdir logs
```


#### To configure everything:

In order for the various scripts to work properly, the ```config.ini``` file contains several variables that need to be set properly according to your environment.

```bash
cp config.ini.sample config.sample
vim config.ini
-> Set the value of the variables іn function of your environment.
:wq
```

At first, it might be difficult to know how to initialize some variables.  Leave them as they are for now and keep reading.  The rest of the documentation should clarify that.


#### To install Maven:

```bash
cd 
wget http://ftp.kddilabs.jp/infosystems/apache/maven/maven-3/3.6.0/binaries/apache-maven-3.6.0-bin.tar.gz
tar zxf apache-maven-3.6.0-bin.tar.gz
```


#### To install Swagger Code Generator:

```bash
git clone https://github.com/swagger-api/swagger-codegen --branch v3.0.3 swagger-codegen-3.0.3
cd swagger-codegen-3.0.3
$MAVEN_HOME/bin/mvn -Dmaven.test.skip=true clean package
java -jar modules/swagger-codegen-cli/target/swagger-codegen-cli.jar generate -i doc/api.waml -l html2 -o /tmp/rest_api
```

Once this is done, you should set the value of ```SwaggerCodegenHome``` variable in the ```config.ini``` file.


#### To generate the HTML page documentating the REST API:

```bash
bin/gen_rest_api_doc
```


#### To manage the accounts

The access to the REST API is private and requires an account.
The current method used to implement the authentication is the Basic Authentication on top of HTTPS.
Eventually, this could be replaced by a more flexible and secure authentication method.

For now, to manage the accounts, it's necessary to edit a .htpasswd file.
This file must be located on a non-web location and must be referred in the .htaccess file at the AuthUserFile directive.
To add users, the htpasswd tool can be used.  Otherwise, it's also possible to edit the file manually using an online tool like
this one found here:

https://www.web2generators.com/apache-tools/htpasswd-generator


#### To deploy the web site on the server:

```bash
bin/deploy_www
```

As this operation is destructive, it's possible to run it with the --dry-run option like this:

```bash
bin/deploy_www --dry-run
```


#### To start the rabbitmq server (on baracuda103):

The request and response queues are implemented as rabbitmt queues. Because of this, we need to run a rabbitmq server.  The easiest way to do that is using a docker image like this:

```bash
docker run -d --rm --hostname rabbitmq-lecturemt --name rabbitmq-lecturemt -p 56080:15672 -p 56010:5672 -e RABBITMQ_DEFAULT_USER=******** -e RABBITMQ_DEFAULT_PASS=******** rabbitmq:3-management
```

Where the proper values must be provided for user and password.

The web interface to rabbitmq will be accessible at http://baracuda103:46080.
The status of the request and response queues can be seen from there.

In case, you need to stop and remove the rabbitmq server:

```bash
docker stop rabbitmq-lecturemt
```


### To start the tensorflow model server (on baracuda103):

If you're using Tensor Flow translation client, you will need to start a Tensor Flow model server.  The easiest way to achieve this is using a docker image, and more specifically, a nvidia-docker image because it's more efficient to use the GPU instead of the CPU.  We do it like this:

```bash
docker run --runtime=nvidia -d --rm -p 46101:8500 -p 46102:8501 --name tensorflow-model-lecturemt --mount type=bind,source=/data/frederic/t2ttrain/bigaspec_withall_from_m101/avg/export/,target=/models/big_aspec_with_all -e MODEL_NAME=big_aspec_with_all -e NVIDIA_VISIBLE_DEVICES=2 tensorflow/serving:1.12.0-gpu
```

In case, you need to stop and remove the rabbitmq server:

```bash
docker stop tensorflow-model-lecturemt
```


#### To start the server:

```bash
python lecturemt/server.py
```


#### To start a translator:

At the moment, the conf/config.ini file is implicitly read by the script in addition to the provided config file on the command-line.
The translator is not linked to the server.  It's rather linked to the queues to which the server is linked.
This indirection allows us to add as many translators as needed dynamically at runtime without restarting the server.
So, in case that the load is too high and that the rabbitmt queues are becoming too full too quickly, it's possible to add translators.
Eventually, this could be done automatically if the availability of the GPU are garanteed.  
It would also be possible to add CPU-bound translators too.

```bash
python lecturemt/translator.py conf/config_translator_ja-en_1.ini conf/config_translator_ja-en_1_logging.ini

```


#### To test a request with the client:

```bash
cat request.json | python lecturemt/client.py
```


#### To stop the server or a translator:

```bash
CTRL+C
```


#### To perform a call using the REST API:

```bash
curl --user guest:guest -X GET $API_BASE_URL/LectureMT/api/1.0/say/Hello
curl --user guest:guest -X GET $API_BASE_URL/LectureMT/api/1.0/api_version
curl --user guest:guest -X GET $API_BASE_URL/LectureMT/api/1.0/server_version
curl --user guest:guest -X GET $API_BASE_URL/LectureMT/api/1.0/translations
curl --user guest:guest -X POST $API_BASE_URL/LectureMT/api/1.0/translation
curl --user guest:guest -X GET $API_BASE_URL/LectureMT/api/1.0/translation/{trans_id}
curl --user guest:guest -X DELETE $API_BASE_URL/LectureMT/api/1.0/translation/{trans_id}
```


### To translate a batch of strings automatically:

```bash
time head -200 /loquat/frederic/LectureMT_data/181213_有機化学\(秋吉先生\)/20181213102652.dat | cut -c21- | tr -d '"'  | bin/translate_batch_messages lotus.kuee.kyoto-u.ac.jp/~frederic/LectureMT/api/1.0 USERNAME PASSWORD DEBUG
```

Where proper values must be provided for USERNAME and PASSWORD.

In this example, the 200 first sentences will be translated.  It's possible to edit the bin/translate_batch_messages script file to adjust the worker_count if needed.  This can be useful if you're using more than one translator. 
