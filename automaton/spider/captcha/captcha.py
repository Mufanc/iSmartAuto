import cv2
import numpy as np
import traceback
from loguru import logger
from numpy import average, dot, linalg
from os import path

base_path = path.join(path.split(__file__)[0], 'models')


def similarity(img_1, img_2):
    try:
        images = [img_1, img_2]
        vectors = []
        norms = []
        for image in images:
            vector = [average(pixels) for pixels in image]
            vectors.append(vector)
            norms.append(linalg.norm(vector, 2))
        a, b = vectors
        a_norm, b_norm = norms
        return dot(a / a_norm, b / b_norm)
    except Exception:
        logger.warning(f'[验证码识别] | 运算出错：\n{traceback.format_exc()}')


def recognize(img_content: bytes):
    try:
        img = cv2.imdecode(np.asarray(bytearray(img_content), dtype=np.uint8), cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)[1]
        models = [cv2.imread(path.join(base_path, f'{i}.png')) for i in range(10)]
        code = ''
        for i in range(4):
            code += sorted(
                [(f'{j}', similarity(img[4:24, 9 + i * 15:24 + i * 15], std)) for j, std in enumerate(models)],
                key=lambda x: x[1], reverse=True
            )[0][0]
        logger.info(f'[验证码识别] | 识别结果：{code}')
        return code
    except Exception:
        logger.warning(f'[验证码识别] | 识别出错：\n{traceback.format_exc()}')
