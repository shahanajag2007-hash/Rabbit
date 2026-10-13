"""Remove the MakeHuman logo print from the white tee texture (male_casualsuit06) -> plain tee."""
import os, cv2, numpy as np
WORK = os.environ.get("AVATAR_WORK", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".work"))
p = os.path.join(WORK, "out", "tex", "male_casualsuit06_diffuse.png")
img = cv2.imread(p, cv2.IMREAD_UNCHANGED)
bgr = img[..., :3]
hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
lum = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
mask = np.zeros(lum.shape, np.uint8)
for (x0, y0, x1, y1) in [(380, 220, 620, 340), (880, 190, 1310, 420), (1480, 300, 1560, 380)]:
    roi = (hsv[y0:y1, x0:x1, 1] > 45) | (lum[y0:y1, x0:x1] < 205)
    mask[y0:y1, x0:x1][roi] = 255
mask = cv2.dilate(mask, np.ones((7, 7), np.uint8), iterations=2)
out = cv2.inpaint(bgr, mask, 9, cv2.INPAINT_TELEA)
if img.shape[2] == 4:
    out = np.dstack([out, img[..., 3]])
cv2.imwrite(p, out)
print("masked px", int((mask > 0).sum()))
