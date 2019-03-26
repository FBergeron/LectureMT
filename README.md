### Some useful things to know.

#### Environment

Prepare a Python virtualenv with the required dependencies:

```bash
virtualenv -p python3 ~/python_envs/web_LectureMT
source ~/python_envs/web_lectureMT
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


#### To start the rabbitmq server (on tulip):

```bash
docker run -d --hostname rabbitmq-lecturemt-dev --name rabbitmq-lecturemt-dev -p 51010:15672 -p 51011:5672 -e  RABBITMQ_DEFAULT_USER=lecturemt-dev -e RABBITMQ_DEFAULT_PASS=****** rabbitmq:3-management

```


#### To start the server:

```bash
python lecturemt/server.py
```


#### To start a translator:

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


#### To stop the rabbitmq server (on tulip):

```bash
docker stop rabbitmq-lecturemt-dev
docler rm rabbitmq-lecturemt-dev
```


#### To remove the rabbitmq server (on tulip):

```bash
docler rm rabbitmq-lecturemt-dev
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


