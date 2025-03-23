
import shutil
import os


file_list = os.listdir('data/')

for f in file_list:

    try:
        src_dir = os.path.join('data/', f)
        des_dir = os.path.join('../frontend/src/data/', f)
        shutil.copyfile(src_dir, des_dir)
        print(f)

    except Exception as e:
        print(e)




