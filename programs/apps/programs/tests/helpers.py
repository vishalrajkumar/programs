"""
Helper methods for testing the processing of image files.

TODO:
    this module was copied (mostly) verbatim from
    edx-platform/master/openedx/core/djangoapps/profile_images/tests/helpers.py
    and could ultimately be moved (with related modules) into a shared utility package.
"""
from contextlib import contextmanager
from cStringIO import StringIO
import os
from tempfile import NamedTemporaryFile

from django.core.files.uploadedfile import UploadedFile, SimpleUploadedFile

import piexif
from PIL import Image


@contextmanager
def make_image_file(dimensions=(320, 240), extension=".jpeg", force_size=None, orientation=None):
    """
    Yields a named temporary file created with the specified image type and
    options.

    The temporary file will be closed and deleted automatically upon exiting
    the `with` block.
    """
    image = Image.new('RGB', dimensions, "green")
    image_file = NamedTemporaryFile(suffix=extension)
    try:
        if orientation and orientation in xrange(1, 9):
            exif_bytes = piexif.dump({'0th': {piexif.ImageIFD.Orientation: orientation}})
            image.save(image_file, exif=exif_bytes)
        else:
            image.save(image_file)
        if force_size is not None:
            image_file.seek(0, os.SEEK_END)
            bytes_to_pad = force_size - image_file.tell()
            # write in hunks of 256 bytes
            hunk, byte_ = bytearray([0] * 256), bytearray([0])
            num_hunks, remainder = divmod(bytes_to_pad, 256)
            for _ in xrange(num_hunks):
                image_file.write(hunk)
            for _ in xrange(remainder):
                image_file.write(byte_)
            image_file.flush()
        image_file.seek(0)
        yield image_file
    finally:
        image_file.close()


@contextmanager
def make_uploaded_file(content_type, *a, **kw):
    """
    Wrap the result of make_image_file in a django UploadedFile.
    """
    with make_image_file(*a, **kw) as image_file:
        yield UploadedFile(
            image_file,
            content_type=content_type,
            size=os.path.getsize(image_file.name),
        )


def make_banner_image_file(name):
    """
    Helper to generate values for program banner_image
    """
    image = Image.new('RGB', (1440, 900), 'green')
    sio = StringIO()
    image.save(sio, format='JPEG')
    return SimpleUploadedFile(name, sio.getvalue(), content_type='image/jpeg')
