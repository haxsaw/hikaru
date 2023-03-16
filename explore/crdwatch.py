from kubernetes import client

api_client = client.ApiClient()

crds = client.CustomObjectsApi(api_client)

crds.list_cluster_custom_object()
