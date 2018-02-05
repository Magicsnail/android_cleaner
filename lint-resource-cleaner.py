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

ANDROID_MANIFEST_FILE = 'AndroidManifest.xml'
PROJECT_FOLDER = 'lint_resource_cleaner'
KEEP_FILE = '/lint-keep.xml'
LINT_RESULT_FILE = '/app/build/reports/lint-results.xml'

TYPE_DRAWABLE = 1
TYPE_LAYOUT = 2
TYPE_STRING = 3

# true表示移除string，false时不移除string
CLEAN_VALUE = False

logfile = open(os.getcwd() + "/lint-log.log", "w");

class Issue:

    """
    Stores a single issue reported by Android Lint
    """

    def __init__(self, filepath, remove_file):
        self.filepath = filepath
        self.remove_file = remove_file
        self.elements = []
        self.type = -1;

    def __str__(self):
        return '{0} {1}'.format(self.filepath, self.elements)

    def __repr__(self):
        return '{0} {1}'.format(self.filepath, self.elements)

    def add_element(self, message):
        res_all = re.findall(self.pattern, message)
        if res_all:
            self._process_match(res_all)
            if (not self.remove_file) and (self.type == TYPE_LAYOUT or self.type == TYPE_DRAWABLE):
                print "No remove: " + message
                pass
        else:
            print("The pattern '%s' seems to find nothing in the error message '%s'. We can't find the resource and "
                  "can't remove it. The pattern might have changed, please check and report this in github issues." % (
                      self.pattern.pattern, message))


class UnusedResourceIssue(Issue):
    pattern = re.compile('The resource `?([^`]+)`? appears to be unused')

    def _process_match(self, match_result):
        bits = match_result[0].split('.')[-2:]
        self.elements.append((bits[0], bits[1]))
        if self.elements[0][0] == 'drawable':
            self.type = TYPE_DRAWABLE
            # 有些Drawable是xml类型的
            if self.filepath.find(self.elements[0][1]) :
                self.remove_file = True
            pass
        elif self.elements[0][0] == 'layout':
            self.type = TYPE_LAYOUT
            if self.filepath.find(self.elements[0][1]) :
                self.remove_file = True
                pass
        elif self.elements[0][0] == 'string':
            self.type = TYPE_STRING


class ExtraTranslationIssue(Issue):
    pattern = re.compile('The resource string \"`([^`]+)`\" has been marked as `translatable=\"false')

    def _process_match(self, match_result):
        self.elements.append(('string', match_result[0]))


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-rm","--remove", help="是否移除资源文件", action="store_true")

    # parser.add_argument('--xml',
    #                     help='Path to the lint result. If not specifies linting will be done by the script',
    #                     default=None)
    # parser.add_argument('--ignore-layouts',
    #                     help='Should ignore layouts',
    #                     action='store_true')
    args = parser.parse_args()

    return args.remove
    # return args.rm, args.app, args.xml, args.ignore_layouts


def get_manifest_string_refs(manifest_path):
    pattern = re.compile('="@string/([^"]+)"')
    with open(manifest_path, 'r') as f:
        data = f.read()
        refs = set(re.findall(pattern, data))
        return [x.replace('/', '.') for x in refs]


def _get_issues_from_location(issue_class, locations, message):
    issues = []
    for location in locations:
        filepath = location.get('file')
        # if the location contains line and/or column attribute not the entire resource is unused.
        # that's a guess ;)
        # TODO stop guessing
        remove_entire_file = (location.get('line') or location.get('column')) is None
        issue = issue_class(filepath, remove_entire_file)
        issue.add_element(message)
        issues.append(issue)
    return issues


def parse_lint_result(lint_result_path, manifest_path):
    """
    Parse lint-result.xml and create Issue for every problem found except unused strings referenced in AndroidManifest
    """
    unused_string_pattern = re.compile('The resource `R\.string\.([^`]+)` appears to be unused')
    unused_drawable_pattern = re.compile('The resource `R\.drawable\.([^`]+)` appears to be unused')
    unused_layout_pattern = re.compile('The resource `R\.layout\.([^`]+)` appears to be unused')
    #mainfest_string_refs = get_manifest_string_refs(manifest_path)
    root = etree.parse(lint_result_path).getroot()
    issues = []

    drawable_cnt =0
    layout_cnt = 0
    string_cnt = 0
    other_cnt = 0
    for issue_xml in root.findall('.//issue[@id="UnusedResources"]'):
        message = issue_xml.get('message')
        
        if re.match(unused_drawable_pattern, message):
            # 处理drawable
            drawable_cnt += 1
            issues.extend(_get_issues_from_location(UnusedResourceIssue,
                issue_xml.findall('location'),
                message))
        elif re.match(unused_layout_pattern, message):
            # 处理layout
            layout_cnt += 1
            issues.extend(_get_issues_from_location(UnusedResourceIssue,
                issue_xml.findall('location'),
                message))
        elif re.match(unused_string_pattern, message):
            # 处理string
            string_cnt +=1
            issues.extend(_get_issues_from_location(UnusedResourceIssue,
                issue_xml.findall('location'),
                message))
        else:
            other_cnt +=1;

    print "【搜索结果】: drawable=%d, layout=%d, string=%d, other=%d" %(drawable_cnt,layout_cnt,string_cnt,other_cnt)
    logfile.write("搜索结果: drawable=%d, layout=%d, string=%d, other=%d" %(drawable_cnt,layout_cnt,string_cnt,other_cnt))

        #unused_string = re.match(unused_string_pattern, issue_xml.get('message'))
        #print message
        #print unused_string

        #has_string_in_manifest = unused_string and unused_string.group(1) in mainfest_string_refs
        #if not has_string_in_manifest:
        #    issues.extend(_get_issues_from_location(UnusedResourceIssue,
        #                                            issue_xml.findall('location'),
        #                                            message))

    # for issue_xml in root.findall('.//issue[@id="ExtraTranslation"]'):
    #     message = issue_xml.get('message')
    #     if re.findall(ExtraTranslationIssue.pattern, message):
    #         issues.extend(_get_issues_from_location(ExtraTranslationIssue,
    #                                                 issue_xml.findall('location'),
    #                                                 message))

    return issues


# 解析keep文件
def __parse_keep_files():
    keepPath = os.getcwd() + KEEP_FILE
    modules =[]
    drawables = []
    drawable_pre = []
    layouts = []
    layout_pre = []

    if os.path.exists(keepPath):
        root = etree.parse(keepPath).getroot()
        for node in root:
            if node.tag == 'drawables':
                for draw in node:
                    file = draw.get('file')
                    pre = draw.get('prefix')
                    if file:
                        drawables.append(os.getcwd() + file)
                        pass
                    elif pre:
                        drawable_pre.append(pre)
                        pass
            elif node.tag == 'layouts':
                for layout in node:
                    file = layout.get('file')
                    pre = layout.get('prefix')
                    if file:
                        layouts.append(os.getcwd() + file)
                        pass
                    elif pre:
                        layout_pre.append(pre)
                    pass
                pass
            elif node.tag == 'modules':
                for modu in node:
                    modules.append(os.getcwd() + modu.get('path'))
                    pass
                pass
    else:
        print '''
        -----------------------------------------------
        >>>lint-keep.xml 未定义，将清理全部文件~
        -----------------------------------------------'''
    return modules, drawables, drawable_pre, layouts, layout_pre


def remove_resource_file(filepath):
    """
    Delete a file from the filesystem
    """
    if os.path.exists(filepath):
        logfile.write('removing: {0}\n'.format(filepath))
        os.remove(os.path.abspath(filepath))

def remove_resource_file_list(list):
    for filepath in list:
        remove_resource_file(filepath)

def has_prefix(list, issue) :
    for node in list :
        if node == issue.elements[0][1][0:len(node)]:
            return True
    return False

def in_module(list, item) :
    for node in list:
        if item[0: len(node)] == node:
            return True
        pass
    return False

def list_has(list, item) :
    for node in list:
        if node == item:
            return True
    return False

def print_filepath_list(prefix, list):
    list.sort()
    for node in list:
        relative_filepath = node[len(os.getcwd()) : ]
        logfile.write(prefix + relative_filepath + "\n")

def __parse_drawable_or_layout_issue(issues, the_type, keep_modules, keep_res, keep_pre):
    total_cnt = 0
    unused_res = []
    ignore_res = []
    
    for issue in issues:
        if not issue.type == the_type:
            continue
        if PROJECT_FOLDER not in issue.filepath :
            print 'ignore %s' % issue.filepath
            continue

        total_cnt += 1
        if issue.remove_file:
            if in_module(keep_modules, issue.filepath) or list_has(keep_res, issue.filepath) or has_prefix(keep_pre, issue):
                ignore_res.append(issue.filepath)
                pass
            else:
                unused_res.append(issue.filepath) 
                pass
        pass
    return total_cnt, unused_res, ignore_res


def _remove_resource_value(issue, filepath):
    """
    Read an xml file and remove an element which is unused, then save the file back to the filesystem
    """
    if os.path.exists(filepath):
        for element in issue.elements:
            print('removing {0} from resource {1}'.format(element, filepath))
            parser = etree.XMLParser(remove_blank_text=False, remove_comments=False,
                                     remove_pis=False, strip_cdata=False, resolve_entities=False)
            tree = etree.parse(filepath, parser)
            root = tree.getroot()
            for unused_value in root.findall('.//{0}[@name="{1}"]'.format(element[0], element[1])):
                root.remove(unused_value)
            with open(filepath, 'wb') as resource:
                tree.write(resource, encoding='utf-8', xml_declaration=True)

def _remove_values(issues) :
    print 'do remove_values....'
    for issue in issues:
        
        if issue.type != TYPE_LAYOUT and issue.type != TYPE_DRAWABLE:
            _remove_resource_value(issue, issue.filepath)
            print 'find value:' + issue.elements[0][0]
            pass
        pass


def handle_unused_resource_issue(remove_mode, issues):
    keep_modules, keep_drawables, keep_drawables_pre, keep_layouts, keep_layouts_pre = __parse_keep_files()
    print '\n【KEEP规则定义】'
    print '\tKeep规则(模块)：%s' % keep_modules
    print '\tKeep规则(Drawable)：%s' % keep_drawables_pre
    print '\tKeep规则(Layout)：%s' % keep_layouts_pre
    print '\n'

    # drawables
    dr_cnt, unused_draw, keep_draw = __parse_drawable_or_layout_issue(issues, TYPE_DRAWABLE, keep_modules, keep_drawables, keep_drawables_pre)
    slog = '【检测结果-Drawable】：总数=%d，可移除=%d，保留=%d : \n' % (dr_cnt, len(unused_draw), len(keep_draw))
    logfile.write('\n\n')
    logfile.write(slog)
    print slog
    if remove_mode:
        remove_resource_file_list(unused_draw)
        pass
    else:
        print_filepath_list('find: ', unused_draw)
        logfile.write('\n\n')
        print_filepath_list('ignore: ', keep_draw)

    # layout
    ly_cnt, unused_layout, keep_layout = __parse_drawable_or_layout_issue(issues, TYPE_LAYOUT, keep_modules, keep_layouts, keep_layouts_pre)
    slog = '【检测结果-Layout】总数=%d，可移除=%d，保留=%d : \n' % (ly_cnt, len(unused_layout), len(keep_layout))
    logfile.write('\n\n')
    logfile.write(slog)
    print slog
    if remove_mode:
        remove_resource_file_list(unused_layout)
        pass
    else:
        print_filepath_list('find: ', unused_layout)
        logfile.write('\n\n')
        print_filepath_list('ignore: ', keep_layout)

    # string 等
    if CLEAN_VALUE:
        _remove_values(issues)
        pass
    pass

def main():
    print ('''
        参数：【-rm】代表移除，默认只检测不做remove；
        
        使用方法：        
		1. 请先确保本文件放在工程根目录下；
		2. 请在执行本脚本之前先执行：./gradlew clean lint命令，生成lint-result.xml；
		3. 有些资源文件是动态使用，因此会存在误检测，为了防止该类型文件被清除，请将其加入到lint-keep.xml文件中；
		''')

    remove = parse_args()

    logfile.write(time.strftime("%Y-%m-%d %H:%M:%S\n", time.localtime()))
    #lint_result_path, app_dir, ignore_layouts = run_lint_command()
    prj_path = os.getcwd(); # 获取当前工作目录
    lint_result_path = prj_path + LINT_RESULT_FILE;
    if os.path.exists(lint_result_path):
        t = os.path.getmtime(lint_result_path)
        st = time.strftime("%Y-%m-%d %H:%M:%S\n", time.localtime(t))
        print 'lint-result创建时间：%s' % st

        if (time.time() - t) > 36000000 :
            print 'lint-result时间超过 [10 Hour], 建议更新代码重新执行：./gradlew clean lint'

        #manifest_path = os.path.abspath(os.path.join('.', ANDROID_MANIFEST_FILE))
        issues = parse_lint_result(lint_result_path, '.')
        handle_unused_resource_issue(remove, issues)
    else:
        print ('''
        执行结果：未找到文件 %s，请根据使用方法完成操作.
		'''  % lint_result_path)

    logfile.close()
    pass


if __name__ == '__main__':
    main()

