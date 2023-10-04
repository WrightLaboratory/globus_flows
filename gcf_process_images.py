""" The function below is used by the transfer-and-compute flow.
It is based on the function `compute_function.py` given in
https://github.com/globus/globus-flows-trigger-examples.

In order to use it, you must first register it with the
Globus Compute service, as described here:
https://globus-compute.readthedocs.io/en/latest/Tutorial.html#registering-a-function
(code is also provided below).

This function generates thumbnail images for all PNG files in the
source_dir and places them in result_path. It moves the source file to
the result path after processing.

Before invoking the function, ensure that you have the Pillow library
(https://python-pillow.org) installed on your Globus Compute endpoint.
"""


def process_images(source_dir=None, destination_dir=None):
    """
    If no source_dir provided, the function exits returning a JSON string reporting nothing done.
    If only source_dir is given, a subdirectory 'processed' will be created under it.
    The resulting thumbnails and the original files will be placed in a YYYYmmdd subfolder of the 
    destination_dir.
    """
    import json
    results = {
        "result": None,
        "thumbnails_generated": []
    }
    if source_dir == None: return json.dumps(results)
    destination_dir = source_dir if (dst := destination_dir) is None else dst


    from datetime import datetime
    from itertools import chain
    from pathlib import Path
    
    from PIL import Image
    from PIL.ExifTags import TAGS


    source_dir = Path(source_dir).expanduser().absolute()

    destination_dir = source_dir.joinpath('processed') if (
        d :=  Path(destination_dir).expanduser().absolute()) == source_dir else d

    paths = chain(
        source_dir.glob('*.png'),
        source_dir.glob('*.jpg'),
        source_dir.glob('*.jpeg')
    )

    image_files = (p for p in paths if p.is_file())

    thumbnails_generated = []

    for img_file in image_files:
        image = Image.open(img_file)

        # Create processed path from metadata
        result_path = None
        exifdata = image.getexif()
        
        d = [exifdata.get(tagid) for tagid in exifdata if TAGS.get(tagid) == 'DateTime'][0]

        image_date = datetime.strptime(d, '%Y:%m:%d %H:%M:%S').strftime('%Y%m%d')
        result_path = destination_dir.joinpath(image_date)
        
        if not (rp := result_path).exists():
            rp.mkdir(parents=True)
        
        # Generate thumbnail
        x_dim = 200
        y_dim = 200
        image.thumbnail(size=(x_dim, y_dim))

        processed_img = result_path.joinpath(f"thumb_{x_dim}x{y_dim}_{img_file.name}")
        processed_img = result_path.joinpath(f"{img_file.stem}_{x_dim}x{y_dim}{img_file.suffix}")
        # Save thumbnail image
        image.save(processed_img)
        
        # mv original to destination to prevent reprocessing
        img_file.rename(processed_img.parent.joinpath(f"{img_file.name}"))
        thumbnails_generated.append(str(processed_img))

    return json.dumps({
        "result": "success",
        "thumbnails_generated": thumbnails_generated
    })


"""Code to register the function with the Globus Compute service
"""

from globus_compute_sdk import Client


def deploy_function():
    client = Client()

    try:
        func_uuid = client.register_function(process_images)
        print(f"Registered 'process_images' function with ID {func_uuid}")
    except Exception as e:
        print(f"Failed to register function: {e}")


def main():
    deploy_function()


if __name__ == "__main__":
    main()

### EOF