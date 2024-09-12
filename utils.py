
# create a python function to generate qr code
# https://medium.com/@rahulmallah785671/create-qr-code-by-using-python-2370d7bd9b8d
# 
from typing import Optional
import io
import base64
import qrcode
from base64 import encodebytes
from PIL import Image, ImageDraw
import random, string

# write python function to return an png image as http response

def foo(image_path):
    template = Image.open(image_path)
    # draw = ImageDraw.Draw(template)
    # draw.text("(553,431)", f"{image_data.text}", fill=4324234, font=font)
    buff = io.BytesIO()
    template.save(buff, format='PNG')
    return buff

def get_response_image(image_path):
    pil_img = Image.open(image_path, mode='r') # reads the PIL image
    byte_arr = io.BytesIO()
    pil_img.save(byte_arr, format='PNG') # convert the PIL image to byte array
    encoded_img = encodebytes(byte_arr.getvalue()).decode('ascii') # encode as base64
    return encoded_img

def generate_qr_code(url: Optional[str] = None) -> str:

    
    # Parse request arguments
    # args = parser.parse_args()
    # Access parsed arguments
    # url = event['url']
    
    # Generate QR code

    
    # Create a QR code object with a larger size and higher error correction
    qr = qrcode.QRCode(version=3, box_size=20, border=10, error_correction=qrcode.constants.ERROR_CORRECT_H)

    uid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
    
    # Define the data to be encoded in the QR code
    
    new_url = f"http://127.0.0.1:5000/pages/{uid}"
    
    print(new_url)
    
    data = new_url or "http://127.0.0.1:5000/main.html"

    # Add the data to the QR code object
    qr.add_data(data)

    # Make the QR code
    qr.make(fit=True)

    # Create an image from the QR code with a black fill color and white background
    img = qr.make_image(fill_color="black", back_color="white")


    
    uri = f"web/static/images/{uid}.png"
    
    # Save the QR code image
    img.save(uri)
    
    return uid

    # Return the QR code as a base64-encoded PNG image
    # return {
    #     'statusCode': 200,
    #     'body': base64.b64encode(buffer.getvalue()).decode('utf-8'),
    #     'isBase64Encoded': True,
    #     'headers': {
    #         'Content-Type': 'image/png'
    #     }
    # }


#write a python function to generate random UUID 

def generate_uuid() -> str:
        
        import uuid
        
        return str(uuid.uuid4())
        
if __name__ == '__main__':
    # generate_qr_code('https://github.com')
    
    print(type(generate_uuid()))