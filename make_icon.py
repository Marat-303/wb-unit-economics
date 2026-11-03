from PIL import Image
img = Image.open('wb_icon.png')
img.save('wb_icon.ico', format='ICO', sizes=[(256, 256)])
print("Иконка wb_icon.ico успешно создана!")