#---------------------------------------------------------------------
#Name: add_contour_result.py
#Menu-en: Add magnetic field strength contour
#Menu-ja: 磁界のコンター追加
#Type: Python
#Create: 2014 JSOL Corporation
#Comment-en: Add magnetic field strength contour definition to the current study.
#Comment-ja: 現在のスタディに磁界のコンタープロットを追加する。
#---------------------------------------------------------------------

import designer

app = designer.GetApplication()

study = app.GetCurrentStudy()

contour = study.CreateContour("AddedByScript")
contour.SetResultType("MagneticFieldStrength")

view = app.View()
view.SetContourView(1)