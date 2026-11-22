from qa_support import *
g=v.Game(VARIANT);g.press(3)
for _ in range(3):g.press(5)
g.press(1,80);g.shot('credits-id')
for label in ['credits-project','credits-endmd2','credits-return-title']:
 g.press(1,80);g.shot(label)
g.e.close();print('credits sequence captured')
