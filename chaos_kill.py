from kubernetes import client, config
import pandas as pd
import schedule
import time
from time import gmtime, strftime

## load configurations
inputs = pd.read_csv('inputs.csv',names=['dep','count'])
inputs

## Load Kube config
config.load_kube_config()
v1 = client.CoreV1Api()

## Get List of Pods that can be stopped, return False if none found:
global_affected_list=[]

def getPods(namespc,inputs):
    pods = v1.list_namespaced_pod(namespace=namespc)
    if not pods.items:
        return None
    else:
        return pd.DataFrame([(pod.metadata.labels.get('app.kubernetes.io/name'),pod.metadata.name,pod.status.phase)\
         for pod in pods.items \
         if (pod.metadata.labels.get('app.kubernetes.io/name') in inputs['dep'].to_list())],columns=['dep','pod','status'])

# doesnt seem to reflect status right after deleting pod
def getVictimStatus(victim):
    df = getPods(namespc,inputs)
    if df is None:
        return None
    else:
        return df[df['pod']==victim]['status'].values[0]
    
def getVictim(podsdf):
    global global_affected_list
    selectedpods = []
    for dep,count in inputs[['dep','count']].values.tolist():
        allpods = podsdf[podsdf['dep']==dep]['pod'].to_list()
        availablepods = [x for x in allpods if x not in global_affected_list]
        selectedpods += list(np.random.choice(availablepods, count))
    global_affected_list += selectedpods
    return selectedpods


### If you JUST want to print which pods are deleted - you can set dryrun=True
### When you are ready to start testing, change dryrun=False
dryrun=False
def job():
    global dryrun
    print(f"{'-'*40}")
    print(f'Run at: {strftime("%Y-%m-%d %H:%M:%S", gmtime())}')
    print(f"{'-'*40}")
    victims = getVictim(getPods('default',inputs))
    if victims is not None:
        print(f"victims are {victims}")
        for victim in victims:
            if not dryrun:
                v1.delete_namespaced_pod(victim,namespc)
            print(f"{victim} pod is deleted")

## Running scheduled chaos test
schedule.every(2).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)