NODE_LABEL = REGION_NAME + '-' + ENV_ID
revision = params.revision

node(NODE_LABEL) {
    try{
    stage('Git Checkout')
        gitCheckOut()
        echo 'Checkout done'
    stage('Build')
        if(params.DOCKER_TAG==''){
             dockerBuild()        
        }
        else{
            echo 'Skipping Build - DOCKER_TAG entered'
        }       
    stage('Deploy')
        echo 'Going to Deploy from jenkins node with label: ' + NODE_LABEL
        deploy()
    stage('Pimp')
        pimp() 
    }
    catch(error){
    stage 'Pimp'
        currentBuild.result = 'FAILURE'
        echo error
        pimp() 
    }
    
    
}

def gitCheckOut(){
    git branch: revision, changelog: false, credentialsId: 'b071d822-ed1a-4270-ac5f-ae12969ee438', poll: false, url: 'git@github.com:pipedrive/jenkins_exporter.git' 
    dir('git_src') {
        env.GIT_COMMIT = sh(returnStdout: true, script: 'git rev-parse HEAD').trim()
        echo 'using env.GIT_COMMIT: ' + env.GIT_COMMIT
   }   
}


def dockerBuild(){
    echo "Docker Build"
    def git_commit_short = env.GIT_COMMIT.substring(0, 10);
    DOCKER_TAG = "${git_commit_short}_${currentBuild.id}"
    DOCKER_IMAGE = "pipedrive/jenkins_exporter"
    env.DOCKER_IMAGE = DOCKER_IMAGE 
    sh(script: "docker build -t ${DOCKER_IMAGE}:${DOCKER_TAG} .")
    env.DOCKER_TAG = DOCKER_TAG
    dockerPush()
    }


def dockerPush(){
    echo "Pushing image:${env.DOCKER_IMAGE} to DockerHub"
    sh(script:"docker push ${env.DOCKER_IMAGE}:${env.DOCKER_TAG}")
    sh(script:"docker tag ${env.DOCKER_IMAGE}:${env.DOCKER_TAG} ${env.DOCKER_IMAGE}:latest")
    sh(script:"docker push ${env.DOCKER_IMAGE}:latest")
    echo "${env.DOCKER_IMAGE}:latest pushed to HUB"
}


def deploy(){
    command = ""
    env.DOCKER_TLS_VERIFY = 1
    fullStackName = REGION_NAME + '_' + ENV_ID + '_' + 'swarm-exporter' 
    if (params.REGION_NAME == "management") {
        if(params.ENV_ID == "test"){
            env.DOCKER_CERT_PATH="/var/lib/jenkins/.docker/swarmee"
            env.DOCKER_HOST = "tcp://local-swarm-manager.pipedrivetest.tools:443"
        }
        if(params.ENV_ID == "live"){
            env.DOCKER_CERT_PATH="/var/lib/jenkins/.docker/swarmee"
            env.DOCKER_HOST = "tcp://local-swarm-manager.pipedrive.tools:443"
        }
        command = "docker-hack stack deploy -c docker-compose.deploy.yml ${fullStackName}"
    }
    print "DOCKER_CERT_PATH = ${DOCKER_CERT_PATH}"
    print "DOCKER_HOST = ${DOCKER_HOST}"
    echo "Fullstackname:${fullStackName}"
    sh(script:command)
}

def pimp(){
    pimpSend pimpEndpoint: "https://pimp.pipedrive.tools/jenkins", eventType: "deploy"
}