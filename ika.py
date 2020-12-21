import cv2
import ffmpeg
import subprocess
import sys

# Installation
# $ pip3 install opencv-python

VIDEO_FILE = ""     # 入力動画ファイルの相対パス コマンドライン引数からでも可
TEMPLATE_FILE = ""  # テンプレ画像の相対パス コマンドライン引数からでも可

MATCH_INTERVAL = 1  # 画像判定の時間間隔
IGNORE_SEC = 5      # 前回killからこの秒数間のkillは同じkill集に含める
MIN_VIDEO_SEC = 10  # kill集の動画の最小長
THREASHOLD = 0.7    # テンプレ画像との合致率閾値

args = sys.argv
if VIDEO_FILE == "":
    VIDEO_FILE = args[1]
if TEMPLATE_FILE == "":
    TEMPLATE_FILE = args[2]

template = cv2.imread(TEMPLATE_FILE, 0)


def match(img, tmp):
    grayimg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 比較用にグレー画像を作る
    result = cv2.matchTemplate(grayimg, tmp, cv2.TM_CCOEFF_NORMED)

    # 0-1 1に近いほど似てる
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    return max_val


def save_match_frame(img, tmp, savefilename):
    # 検出結果から検出領域の位置を取得
    grayimg = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # 比較用にグレー画像を作る
    result = cv2.matchTemplate(grayimg, tmp, cv2.TM_CCOEFF_NORMED)

    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    top_left = max_loc
    w, h = tmp.shape[::-1]
    bottom_right = (top_left[0] + w, top_left[1] + h)

    print(max_val, min_val)

    # 検出領域を四角で囲んで保存
    if(max_val >= THREASHOLD):
        cv2.rectangle(img, top_left, bottom_right, (0, 0, 255), 2)
        cv2.imwrite(savefilename, img)


def save_match_video(originfilename, start_time, length, savefilename):
    cmd = "ffmpeg -ss " + str(start_time) + " -i " + originfilename + \
        " -ss 0 -t " + str(length) + " " + savefilename
    subprocess.call(cmd, shell=True)


video = cv2.VideoCapture(VIDEO_FILE)

frame_count = int(video.get(7))  # 総フレーム数
frame_rate = int(video.get(5))  # フレームレート

kill_times = [{"start": 0, "end": 0}]

for i in range(int((frame_count / frame_rate)/MATCH_INTERVAL)):  # 指定した間隔秒(frame数)ごとに画像判定
    video.set(cv2.CAP_PROP_POS_FRAMES, frame_rate * MATCH_INTERVAL * i)
    _, frame = video.read()  # 動画をフレームに読み込み
    # save_match_result(frame, template, "test" + str(i) + ".png")

    checkVal = match(frame, template)

    if checkVal < THREASHOLD:
        continue

    if (i * MATCH_INTERVAL) - kill_times[-1]["end"] >= IGNORE_SEC:
        # 前回のkillタイミングから、ignore_seconds以上たった後killしていた場合は、リストに追加
        kill_time = {
            "start": i * MATCH_INTERVAL - MIN_VIDEO_SEC,
            "end": i * MATCH_INTERVAL
        }
        kill_times.append(kill_time)

        print("[Found!] kill_time [s]: " +
              str(kill_time["start"]) + " - " + str(kill_time["end"]))
        continue

    if (i * MATCH_INTERVAL) - kill_times[-1]["end"] < IGNORE_SEC:
        # 前回のkillタイミングから、ignore_seconds未満でkillしていた場合は、その分だけ動画長を長くする
        kill_times[-1]["end"] = i * MATCH_INTERVAL
        print("  + [len update] kill_time [s]: " + str(kill_times[-1]
                                                       ["start"]) + " - " + str(kill_times[-1]["end"]))

del kill_times[0]

for t in kill_times:
    save_match_video(
        VIDEO_FILE,                                         # 元動画ファイル
        t["start"],                                         # クリップ開始位置
        t["end"] - t["start"] + 1,                          # 動画長
        VIDEO_FILE + "_kill_" + str(t["start"]) + ".mp4"    # 抽出後動画ファイル名
    )
