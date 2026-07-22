#---------------------------------------------------------------------
#Name: set_current.py
#Menu-en: Add current condition to coils
#Menu-ja: コイルに電流条件を追加
#Type: Python
#Create: 2014 JSOL Corporation
#Comment-en: Set a current condition on all parts named "Coil" in the current study.
#Comment-ja: 現在のスタディで、名前が「コイル」の部品に対して電流条件を設定する。
#---------------------------------------------------------------------

from designer import *

def main():      
	DeApp = GetApplication()
	study =  DeApp.GetCurrentStudy()
	if study.IsValid() == 0:
		MsgBox("No current study")
		return

	model = DeApp.GetCurrentModel()
	selection =model.CreateSelection()
	selection.SelectPart("Coil")

	if selection.NumParts() == 0:
		MsgBox("Coil parts cannot be found")
		return

	current = study.CreateCondition("Current","Current/Coil")
	point = DeApp.CreatePoint(-5.925, 0.237231, -4.85)
	direction = DeApp.CreatePoint(0,1,0)
	current.SetPointWithUnit ("origin", point,"mm")
	current.SetPointWithUnit ("direction", direction,"mm")

	current.AddSelected(selection)
	selection.Clear()
	amp = 0.0216
	turn = 14600
	current.SetValue( "current", amp)	
	current.SetValue( "turn", turn)	

if __name__ == "__main__":
    main()
