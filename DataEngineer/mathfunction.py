# -*- coding: utf-8 -*-
import numpy as np

def outlier_iqr(data, column, result_type):

	# lower, upper 글로벌 변수 선언하기
	global lower, upper
	
	# 4분위수 기준 지정하기
	q25, q75 = np.quantile(data[column], 0.25), np.quantile(data[column], 0.75)
	
	# IQR 계산하기	
	iqr = q75 - q25
	
	# outlier cutoff 계산하기
	cut_off = iqr * 1.5
	
	# lower와 upper bound 값 구하기
	lower, upper = q25 - cut_off, q75 + cut_off
	
	print('IQR은',iqr, '이다.')
	print('lower bound 값은', lower, '이다.') 
	print('upper bound 값은', upper, '이다.')
	
	# 1사 분위와 4사 분위에 속해있는 데이터 각각 저장하기
	up = data[data[column] > upper]
	low = data[data[column] < lower]
	if result_type == "low": 
		return low
	elif result_type == "up":
		return up
	else:
		return low, up