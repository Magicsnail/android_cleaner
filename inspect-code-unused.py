# encoding: utf-8

import argparse
import os
import re
import subprocess
import distutils.spawn
import time
from lxml import etree
import time
import datetime

UNUSED_XML = "unused.xml" #inspect code 生成的文件名称；


# 解析参数
def __parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-f", "--file", help="待分析的文件folder", default="null")
	args = parser.parse_args()
	return args.file


def __parse_unused_class(filepath, logfile) :
	cls_instant = []
	cls_construct = {}
	cls_other = {}
	
	root = etree.parse(filepath).getroot()
	for node in root :
		clspath = ''
		desc = ''
		file = ''
		for subnode in node :
			if subnode.tag == 'file':
				file = subnode.text
				pass
			elif subnode.tag == 'entry_point':
				clspath = subnode.get('FQNAME')
				pass
			elif subnode.tag == 'description':
				desc = subnode.text
				pass
		if desc == 'Class is not instantiated.':
			cls_instant.append(clspath);
		elif desc == 'Constructor is never used.':
			cls_construct[clspath.split(' ')[0]] = 1
			pass
		else:
			cls_other[clspath.split(' ')[0]] = 1

	logfile.write(">>>> Class is not instantiated.\n")
	for s in cls_instant:
		logfile.write(s)
		logfile.write('\n')
		pass

	logfile.write('\n\n\n>>>> Constructor is never used.\n')
	for s in cls_construct.keys():
		logfile.write(s)
		logfile.write('\n')

	logfile.write('\n\n\n>>>> other\n')
	for s in cls_other.keys():
		logfile.write(s)
		logfile.write('\n')

	return len(cls_instant) + len(cls_construct) + len(cls_other)


def main() :
	print '''
	参数：
	【-f】：必选，指定待检测的文件所在的目录全路径，生成的结果文件也放在同级目录；

	示例：
	python %s -f /User/xxx/code/

	使用说明：
	基于Android Studio V3.0版本。该方式检测不出Activity，因此更大的清理还需要日常开发时的主动关注。
	针对Android Studio的Analyse/Inspect Code静态分析工具生成的分析结果文件做的解析。
	Inspect Code时间较长，建议根据需要设置检测范围（包括检测的module和检测选项，检测选项在检测面板中设置）。
	如果仅检测无用代码请选择[Unused declaration]。
	另外由于该工具检测并不完善，比如一个类存在几个变量都未使用，仅会报unused fields，不会报class的unused，因此输出的结果需要我们人工挨个排查。
	''' % __name__
	folder = __parse_args()
	file = '%s/%s' %(folder,UNUSED_XML)
		# file = '/Users/cheney/Documents/unused.xml'
	if not os.path.exists(file) :
		print file
		print "执行结果：失败！请通过参数 -f 指定正确的文件夹目录."
	else :
		logfile = open("%s/lint-log.log" %folder, "w");
		size = __parse_unused_class(file, logfile)
		print '执行结果：成功. 共发现 %d条记录' % size
		pass
	
	pass

if __name__ == '__main__':
    main()
    pass
