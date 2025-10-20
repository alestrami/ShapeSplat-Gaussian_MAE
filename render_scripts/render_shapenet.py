import os
import time
import argparse
import trimesh
import json
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--model_root_dir", type=str, default="./shapenet/ShapeNetCore.v1")
parser.add_argument(
    "--render_root_dir", type=str, default="./shapenet/ShapeNetCore.v1/render"
)  # blender_render
parser.add_argument("--file_dict_path", type=str, default="./shapnetv1_data_dict.json")
parser.add_argument(
    "--start_idx", type=int, default=0, help="start scene you want to train."
)
parser.add_argument("--end_idx", type=int, default=10, help="end scene you want to end")
parser.add_argument(
    "--blender_location",
    type=str,
    default="./blender_install/blender-3.6.13-linux-x64/blender",
)
parser.add_argument("--num_thread", type=int, default=10, help="1/3 of the CPU number")
parser.add_argument("--shapenetversion", type=str, default="v1", help="v1 or v2")
parser.add_argument("--debug", type=bool, default=False)
parser.add_argument("--category", type=str, default=None, help="ShapeNet category ID to render")
FLAGS = parser.parse_args()

model_root_dir = FLAGS.model_root_dir
render_root_dir = FLAGS.render_root_dir


def gen_obj(model_root_dir, cat_id, obj_id):
    t_start = time.time()
    if FLAGS.shapenetversion == "v2":
        objpath = os.path.join(
            model_root_dir, cat_id, obj_id, "models", "model_normalized.obj"
        )
    else:
        objpath = os.path.join(model_root_dir, cat_id, obj_id, "model.obj")  # for v1

    obj_save_dir = os.path.join(render_root_dir, cat_id, obj_id)
    os.makedirs(obj_save_dir, exist_ok=True)

    # "There is no item named '000.png' in the archive” error
    run_flag = True
    # check generated image.zip image number
    if os.path.exists(os.path.join(obj_save_dir, "image.zip")):
        print("exist image.zip, sanity check", obj_save_dir)
        try:
            with zipfile.ZipFile(
                os.path.join(obj_save_dir, "image.zip"), "r"
            ) as zip_ref:
                zip_contents = zip_ref.namelist()
                if len(zip_contents) == 72:
                    print("Exist!!!, skip %s %s" % (cat_id, obj_id))
                    run_flag = False
                else:
                    print(
                        "missing render images", len(zip_contents), cat_id, obj_id
                    )  # 41f9be4d80af2c709c12d6260da9ac2b
                    run_flag = True
        except:
            pass

    elif not os.path.exists(objpath):
        print("Non-Exist object model!!!, skip %s %s" % (cat_id, obj_id))
        run_flag = False

    if run_flag:
        print("Start %s %s" % (cat_id, obj_id))
        render_script = "/leonardo_work/IscrC_GEN-X3D/GS/ShapeSplat-Gaussian_MAE/render_scripts/render_blender.py"
        if FLAGS.debug:
            # save to  point cloud
            mesh = trimesh.load(objpath, force="mesh")
            mesh.export(os.path.join(obj_save_dir, "point_cloud.obj"))
            cmd = (
                f"unset PYTHONPATH PYTHONHOME; "
                f"{FLAGS.blender_location}  --background --python {render_script} "
                f"-- --views {72} --obj_save_dir {obj_save_dir} {objpath}"
            )
            os.system(cmd)

        else:
            mesh = trimesh.load(objpath, force="mesh")
            mesh.export(os.path.join(obj_save_dir, "point_cloud.obj"))
            try:
                os.system(
                    FLAGS.blender_location
                    + " --background --python render_blender.py -- --views %d --obj_save_dir %s  %s > /dev/null 2>&1"
                    % (72, obj_save_dir, objpath)
                )
            except Exception:
                print("Generating error")
                print("====================")

        print("Finished %s %s" % (cat_id, obj_id), time.time() - t_start)


with open(FLAGS.file_dict_path, "r") as f:
    data_dict = json.load(f)

model_root_dir_lst = []
cat_id_lst = []
obj_id_lst = []

if FLAGS.category is not None:
    # Only use the selected category
    if FLAGS.category not in data_dict:
        raise ValueError(f"Category {FLAGS.category} not found in data_dict")
    obj_ids = data_dict[FLAGS.category]
    # Slice within category using start_idx / end_idx
    obj_ids = obj_ids[FLAGS.start_idx : FLAGS.end_idx if FLAGS.end_idx != -1 else None]
    model_root_dir_lst = [model_root_dir] * len(obj_ids)
    cat_id_lst = [FLAGS.category] * len(obj_ids)
    obj_id_lst = obj_ids
else:
    # Original behavior: flatten all categories
    for cat_id in data_dict.keys():
        obj_ids = data_dict[cat_id]
        model_root_dir_lst.extend([model_root_dir] * len(obj_ids))
        cat_id_lst.extend([cat_id] * len(obj_ids))
        obj_id_lst.extend(obj_ids)
    # Apply global start/end slicing
    if FLAGS.end_idx == -1 or FLAGS.end_idx > len(obj_id_lst):
        FLAGS.end_idx = len(obj_id_lst)
    model_root_dir_lst = model_root_dir_lst[FLAGS.start_idx : FLAGS.end_idx]
    cat_id_lst = cat_id_lst[FLAGS.start_idx : FLAGS.end_idx]
    obj_id_lst = obj_id_lst[FLAGS.start_idx : FLAGS.end_idx]


print("total length of obj_total_path", len(obj_id_lst))

print("sub_scenes_list", len(model_root_dir_lst))

for model_root_dir, cat_id, obj_id in zip(model_root_dir_lst, cat_id_lst, obj_id_lst):
    gen_obj(model_root_dir, cat_id, obj_id)