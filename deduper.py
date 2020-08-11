from PIL import Image
from difflib import SequenceMatcher
import hashlib, os, imagehash, argparse

# Setup arguments
parser = argparse.ArgumentParser(description="Image deduplicator")
parser.add_argument('-m', '--mode', help="Deduplicator operation mode (rename, move, organize, similar, all)", required=True)
parser.add_argument('-p', '--path', help="Path to files to process", required=True)
parser.add_argument('-d', '--duplicate-path', help="Define path to dump duplicate images")
parser.add_argument('-q', '--quiet', help="Do not display any output", action='store_true')
parser.add_argument('-v', '--verbose', help="Displat additional messages", action='store_true')

args = parser.parse_args()

# Massage args for input
if args.quiet == True and args.verbose == True:
    args.quiet = False
args.mode = args.mode.split("+")

# Setup global vars
hasher = hashlib.md5()
directory = args.path
duplicate_dir = args.duplicate_path if args.duplicate_path is not None else "{0}~duplicates".format(directory)
skip_dir_nums = []
skip_dirs = []
files = []

# Message filter function
def __print(msg, level=None):
    if args.quiet != True:
        if args.verbose == True and level == "verbose":
            print(msg)
        else:
            print(msg)
    elif level == "error":
        print(msg)

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

def generate_similarity_report(similarities, parent_dir):
    html = r'<html><head><style>.left_info,.right_info{margin-bottom:5px}body{width:810px;background-color:#333;color:#cec}.similar_set{height:400px;width:810px;margin:40px;margin-bottom:60px}div.left_image,div.right_image{float:left;background-color:#444}div.left_image{margin-right:5px}img.image_a,img.image_b{max-height:400px;max-width:400px}</style></head><body>'
    for key, value in similarities.items():
        a, b, a_info, b_info, similarity, truth = value
        html += "<div class='similar_set' id='%s'><div>Similarity: %s (%s)</div>" % (key, similarity, truth)
        html += "<div class='left_image'><div class='left_info'>%s</div><img class='image_a' src='%s' /></div>" % (a_info, os.path.join(parent_dir, a))
        html += "<div class='right_image'><div class='right_info'>%s</div><img class='image_b' src='%s' /></div>" % (b_info, os.path.join(parent_dir, b))
        html += "</div>"
    html += "</body></html>"
    return html

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def generate_skip_dirs():
    for skip_dir_num in skip_dir_nums:
        skip_dirs.append(os.path.join(directory, "{0}".format(skip_dir_num)))

def get_hash(file_path):
    hash = imagehash.average_hash(Image.open(file_path))
    return hash

def move_duplicate(file_path, file_hash, file_ext):
    if not os.path.exists(duplicate_dir):
        os.makedirs(duplicate_dir)
    duplicate_path = os.path.join(duplicate_dir, "{0}{1}".format(file_hash, file_ext))
    if os.path.isfile(duplicate_path) == True:
        os.remove(file_path)
        __print("Deleting extra duplicate {0} ({1})".format(file_path, duplicate_path))
        return
    os.rename(file_path, duplicate_path)
    __print("Moving {0}{1} to duplicate image directory".format(file_hash, file_ext))

def rename_file(file_path):
    file_hash = get_hash(file_path)
    file_ext = os.path.splitext(file_path)[1]
    old_file_name = os.path.basename(file_path)
    new_file_name = "{0}{1}".format(file_hash, file_ext)
    new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
    
    # If old_file_name and new_file_name do not match, rename file
    if old_file_name != new_file_name:
        if os.path.isfile(new_file_path):
            move_duplicate(file_path, file_hash, file_ext)
        else:
            os.rename(file_path, new_file_path)
            __print("{2} {0} -> {1}".format(old_file_name, new_file_name, os.path.dirname(file_path).replace(directory, "")))
    if new_file_name not in files:
        files.append(new_file_name)
    else:
        move_duplicate(file_path, file_hash, file_ext)

def move_file(file_path, destination):
    file_name = os.path.basename(file_path)
    new_file_path = os.path.join(destination, file_name)
    if file_path != new_file_path:
        if os.path.isfile(new_file_path) == False:
            os.rename(file_path, new_file_path)
            __print("Moving {0} -> {1}".format(file_name, new_file_path.replace(directory, "").replace("\\", "/")))
        else:
            move_duplicate(file_path, get_hash(file_path), os.path.splitext(file_path)[1])

def organize_file(file_path):
    file_name = os.path.basename(file_path)
    destination = os.path.join(directory, file_name[:1])
    
    if not os.path.exists(destination):
        os.makedirs(destination)

    move_file(file_path, destination)

def validate_file_type(file):
    extension = os.path.splitext(file)[1]
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif"]
    return extension in valid_extensions

def get_files_and_rename(parent_dir):
    if parent_dir is not duplicate_dir and parent_dir not in skip_dirs:

        for file in os.listdir(parent_dir):
            file_path = os.path.join(parent_dir, file)
            if os.path.isfile(file_path):
                if validate_file_type(file_path):
                    try:
                        rename_file(file_path)
                    except:
                        __print("There was an error handling %s" % (file_path), "error")
                        pass
            else:
                get_files_and_rename(file_path)

def get_files_and_move(parent_dir):
    if parent_dir not in skip_dirs:
        for file in os.listdir(parent_dir):
            file_path = os.path.join(parent_dir, file)
            if os.path.isfile(file_path):
                move_file(file_path, os.path.join(directory, "~unsorted"))
            else:
                get_files_and_move(file_path)

def get_files_and_organize(parent_dir):
    if parent_dir not in skip_dirs:
        for file in os.listdir(parent_dir):
            file_path = os.path.join(parent_dir, file)
            if os.path.isfile(file_path):
                organize_file(file_path)
            else:
                get_files_and_organize(file_path)

def get_files_and_find_similar(parent_dir):
    if parent_dir not in skip_dirs:
        similar_sets = {}
        for file in os.listdir(parent_dir):
            for index in os.listdir(parent_dir):
                similarity = similar(file.split(".")[0], index.split(".")[0])
                if similarity >= 0.8 and similarity < 1.0:
                    hash_file = hash(file)
                    hash_index = hash(index)
                    hash_combination = hash_file + hash_index
                    if hash_combination not in similar_sets:
                        file_path = os.path.join(parent_dir, file)
                        file_stat = os.stat(file_path)
                        file_size = sizeof_fmt(file_stat.st_size)
                        file_ext  = os.path.splitext(file_path)[1].replace(".", "")
                        file_info = "%s, %s" % (file_size, file_ext)
                        file_img  = Image.open(file_path)
                        file_hash = imagehash.average_hash(file_img)

                        index_path = os.path.join(parent_dir, index)
                        index_stat = os.stat(index_path)
                        index_size = sizeof_fmt(index_stat.st_size)
                        index_ext  = os.path.splitext(index_path)[1].replace(".", "")
                        index_info = "%s, %s" % (index_size, index_ext)
                        index_img  = Image.open(index_path)
                        index_hash = imagehash.average_hash(index_img)

                        true_similarity = file_hash - index_hash
                        if true_similarity < 3:
                            similar_sets[hash_combination] = [file, index, file_info, index_info, "%d%%" % (similarity * 100), true_similarity]
                            __print('Similarity [%d] found between %s and %s (%d%%)' % (len(similar_sets), file, index, similarity * 100), None)
                        else:
                            __print("Not similar enough...", None)
                    else:
                        __print("Duplicate similarity found, discarding... (%s, %s)" % (file, index), None)
        __print("Similarities found: %d" % (len(similar_sets)), None)
        html = generate_similarity_report(similar_sets, parent_dir)
        with open("report.html", "w") as outfile:
            outfile.write(html)
        os.system("start report.html")

generate_skip_dirs()

if "similar" in args.mode:
    get_files_and_find_similar(directory)
if "rename" in args.mode:
    get_files_and_rename(directory)
if "move" in args.mode:
    get_files_and_move(directory)
if "organize" in args.mode:
    get_files_and_organize(directory)

# Example usage to rename files in a folder and detect duplicate within
# python .\deduper.py -m rename -p C:\path\ -v

# Example usage to organize files, including any that are unorganized, within a directory and all subdirectories
# python .\deduper.py -m organize -p C:\path\