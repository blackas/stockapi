# -*- coding: utf-8 -*-
import numpy as np

def outlier_iqr(data, column, result_type, row_rate=0.25, up_rate=0.75, weight=2):

	# lower, upper 글로벌 변수 선언하기
	global lower, upper

	if row_rate + up_rate != 1:
		return -1
	
	# 4분위수 기준 지정하기
	q25, q75 = np.quantile(data[column], row_rate), np.quantile(data[column], up_rate)
	
	# IQR 계산하기	
	iqr = q75 - q25
	
	# outlier cutoff 계산하기
	cut_off = iqr * weight
	
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