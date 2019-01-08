### Some useful things to know.

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


#### To deploy the web site on the server:

```bash
bin/deploy_www
```

As this operation is destructive, it's possible to run it with the --dry-run option like this:

```bash
bin/deploy_www --dry-run
```

