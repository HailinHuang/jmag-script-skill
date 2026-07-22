#---------------------------------------------------------------------
#Name: run_all_projects.py
#Menu-en: Run all studies
#Menu-ja: 全スタディの解析実行
#Type: Python
#Create: 2014 JSOL Corporation
#Comment-en:Run all studies in the project.
#Comment-ja:プロジェクトの全てのスタディを実行する。
#---------------------------------------------------------------------

import designer

app = designer.GetApplication()

count = 0
num = app.NumStudies()
while count < num:
	st = app.GetStudy(count)
	if (st.HasResult() != 1):
		st.Run()
	count = count + 1

print('This script ran %i studies.' %count)

