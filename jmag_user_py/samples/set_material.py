#---------------------------------------------------------------------
#Name: set_material.py
#Menu-en: Set the coil material
#Menu-ja: コイル材料を設定
#Type: Python
#Create: 2014 JSOL Corporation
#Comment-en: Sets the material for parts in the current study named "Coil" to copper.
#Comment-ja: 現在のスタディで、名前が「コイル」の部品に対して材料を銅に設定する。
#---------------------------------------------------------------------

from designer import *

def main():      
	DeApp = GetApplication()
	study =  DeApp.GetCurrentStudy()
	if study.IsValid() == 0:
		MsgBox("No current study")
		return

	copper = DeApp.CreateMaterial("Copper")
	study.SetMaterial ("Coil",(copper))

if __name__ == "__main__":
    main()
