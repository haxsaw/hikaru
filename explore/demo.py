from hikaru.generate import load_full_yaml, get_yaml, get_python_source

f = open("pod-minimal.yaml", "r")
docs = load_full_yaml(stream=f)
p = docs[0]
print(get_yaml(p))
print(get_python_source(p, assign_to='x'))
