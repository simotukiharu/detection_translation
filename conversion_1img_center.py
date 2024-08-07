import sys, os
sys.dont_write_bytecode = True
import torch
from torch import nn
import torchvision.transforms as T
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pathlib
import random
import cv2
import config as cf
import composition_center

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(DEVICE)
model_path = sys.argv[1] # モデルのパス
image_path = sys.argv[2] # 入力画像のパス
file_name = pathlib.Path(sys.argv[2])
np.set_printoptions(precision=3, suppress=True) # 指数表現をやめて小数点以下の桁数を指定する
out_dir = pathlib.Path(sys.argv[3])
if(not out_dir.exists()): out_dir.mkdir() #フォルダがない時に作る

# フォントの設定
textsize = 16
linewidth = 3
font = ImageFont.truetype("_FiraMono-Medium.otf", size=textsize)

# モデルの定義と読み込みおよび評価用のモードにセットする
model = cf.build_model()
if DEVICE == "cuda":  model.load_state_dict(torch.load(model_path))
else: model.load_state_dict(torch.load(model_path, torch.device("cpu")))
model.to(DEVICE)
model.eval()

data_transforms = T.Compose([T.ToTensor()])

# 画像の読み込み・変換
img = Image.open(image_path).convert('RGB') # カラー指定で開く
input_rgb = np.array(img) 
i_w, i_h = img.size
print(i_w, i_h)
data = data_transforms(img)
data = data.unsqueeze(0) # テンソルに変換してから1次元追加

data = data.to(DEVICE)
outputs = model(data) # 推定処理
# print(outputs)
bboxs = outputs[0]["boxes"].detach().cpu().numpy()
scores = outputs[0]["scores"].detach().cpu().numpy()
labels = outputs[0]["labels"].detach().cpu().numpy()
# print(bboxs, scores, labels)

draw = ImageDraw.Draw(img)
box_col = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
mx0, my0, mx1, my1 = [], [], [], []
for i in range(len(scores)):
    b = bboxs[i]
    # print(b)
    prd_val = scores[i]
    if prd_val < cf.thDetection: continue # 閾値以下は飛ばす
    prd_cls = labels[i] 

    x0, y0 = b[0], b[1]
    p0 = (int(x0), int(y0)) #矩形の左上の座標
    p1 = (int(b[2]), int(b[3])) #矩形の右下の座標

    # 領域の座標を配列に
    mx0.append(b[0])
    my0.append(b[1])
    mx1.append(b[2])
    my1.append(b[3])

    w_side = b[2] - x0
    h_side = b[3] - y0
    # print(w_side, h_side)

    draw.rectangle((p0, p1), outline=box_col[prd_cls], width=linewidth) # 枠の矩形描画
    text = f" {prd_cls}  {prd_val:.3f} " # クラスと確率
    # txw, txh = draw.textsize(text, font=font) # 表示文字列のサイズ
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font) # 表示文字列のサイズ
    txw, txh = right - left, bottom - top
    txpos = (x0, y0 - textsize - linewidth // 2) # 表示位置
    draw.rectangle([txpos, (x0 + txw, y0)], outline=box_col[prd_cls], fill=box_col[prd_cls], width=linewidth)
    draw.text(txpos, text, font=font, fill=(255, 255, 255))

print(prd_cls, prd_val, p0, p1)
#矩形のシェイプ
    
# 検出した矩形が複数あった場合の平均の処理
mean_p0 = (int(np.mean(mx0)), int(np.mean(my0)))
mean_p1 = (int(np.mean(mx1)), int(np.mean(my1)))
    
input_bgr = cv2.cvtColor(input_rgb, cv2.COLOR_RGB2BGR)
dst_img = composition_center.center(input_bgr, mean_p0, mean_p1)

cv2.imwrite(f'{out_dir}/dst_{prd_cls}_{file_name.stem}.png', dst_img)

img.save(f"{file_name.stem}_det.png") #.stemでフォルダ内の処理
input_rgb = np.array(img)
input_bgr = cv2.cvtColor(input_rgb, cv2.COLOR_RGB2BGR)
dst_img = composition_center.center(input_bgr, mean_p0, mean_p1)

cv2.imwrite(f'{out_dir}/dst_{prd_cls}_{file_name.stem}_bbox.png', dst_img)