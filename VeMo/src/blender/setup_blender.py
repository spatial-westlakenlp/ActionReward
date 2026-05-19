import subprocess
import sys
print(sys.executable)
dependencies = ['joblib', 'torch', 'numpy', 'scipy', 'trimesh', 'xml-python', 'imageio', 'Pillow']
subprocess.run([sys.executable, "-m", "ensurepip"])
subprocess.run([sys.executable, "-m", "pip", "install"] + dependencies)