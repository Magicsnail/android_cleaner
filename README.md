# lint_resource_cleaner
# 用于清理工程中无效资源
参考了android-resource-remover编写，但基本算是重构了，本脚本是以大型工程为依据编写，具有更强大的适应能力，android-resource-remover因为keep方式原始，同时remove等存在一些bug，因此本工程脚本做了重构。

- 增加了强大的keep机制，详见lint-keep.xml文件。
- 直接Android Studio执行python脚本文件lint-resource-cleaner.py即可。
- 默认脚本只执行检测并输出结果，-rm参数用来执行remove，结果输出到lint.log文件中。

