from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
Image.MAX_IMAGE_PIXELS=16000000

def clean_image(upload):
    if upload.size>5*1024*1024: raise ValidationError('Fotografija je prevelika (najviše 5 MB).')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(upload) as img:
                if img.format not in {'JPEG','PNG','WEBP'}: raise ValidationError('Dopuštene su JPEG, PNG i WebP slike.')
                if getattr(img,'n_frames',1)!=1: raise ValidationError('Animirane slike nisu dopuštene.')
                img.load();img=ImageOps.exif_transpose(img)
                img.thumbnail((1600,1600))
                rgb=Image.new('RGB',img.size,'white')
                if img.mode in ('RGBA','LA'):
                    rgba=img.convert('RGBA');rgb.paste(rgba,mask=rgba.getchannel('A'))
                else: rgb.paste(img.convert('RGB'))
                out=BytesIO();rgb.save(out,'JPEG',quality=88,optimize=True)
        return ContentFile(out.getvalue(),name='product.jpg')
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValidationError('Fotografiju nije moguće sigurno obraditi.')
