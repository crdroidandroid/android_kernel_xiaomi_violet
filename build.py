import os
import sys
import subprocess
import string
import random

bashfile=''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
bashfile='/tmp/'+bashfile+'.sh'

f = open(bashfile, 'w')
s = """#!/bin/bash
# Telegram Config
TOKEN=$(/usr/bin/env python -c "import os; print(os.environ.get('TOKEN'))")
CHATID=$(/usr/bin/env python -c "import os; print(os.environ.get('CHATID'))")
BOT_MSG_URL="https://api.telegram.org/bot${TOKEN}/sendMessage"
BOT_BUILD_URL="https://api.telegram.org/bot${TOKEN}/sendDocument"
# Build Machine details
cores=$(lscpu | grep "Core(s) per socket" | awk '{print $NF}')
os=$(cat /etc/issue)
time=$(TZ="Asia/Dhaka" date "+%a %b %d %r")
# send saxx msgs to tg
tg_post_msg() {
  curl -s -X POST "$BOT_MSG_URL" -d chat_id="$CHATID" \\
    -d "disable_web_page_preview=true" \\
    -d "parse_mode=html" \\
    -d text="$1"
}
# send build to tg
tg_post_build()
{
	#Post MD5Checksum alongwith for easeness
	MD5CHECK=$(md5sum "$1" | cut -d' ' -f1)
	#Show the Checksum alongwith caption
	curl --progress-bar -F document=@"$1" "$BOT_BUILD_URL" \\
	-F chat_id="$CHATID"  \\
	-F "disable_web_page_preview=true" \\
	-F "parse_mode=Markdown" \\
	-F caption="$2 | *MD5 Checksum : *\\`$MD5CHECK\\`"
}

kernel_dir="${PWD}"
CCACHE=$(command -v ccache)
objdir="${kernel_dir}/out"
anykernel=$HOME/anykernel
builddir="${kernel_dir}/build"
ZIMAGE=$kernel_dir/out/arch/arm64/boot/Image.gz-dtb
kernel_name="perf_violet_13-14-dynamic"
KERVER=$(make kernelversion)
COMMIT_HEAD=$(git log --oneline -1)
zip_name="$kernel_name-$(date +"%d%m%Y-%H%M")-signed.zip"
TC_DIR=$HOME/tc/
CLANG_DIR=$TC_DIR/clang-r510928
export CONFIG_FILE="vendor/violet-perf_defconfig"
export ARCH="arm64"
export KBUILD_BUILD_HOST=arch
export KBUILD_BUILD_USER=kibria5
LINUX_COMPILE_BY="kibria5"
LINUX_COMPILE_HOST="arch"
export PATH="$CLANG_DIR/bin:$PATH"
export CI_BRANCH=$(git rev-parse --abbrev-ref HEAD)

tg_post_msg "<b>Kernel : </b><code>$kernel_name</code>%0A<b>Upstream Version : </b><code>$KERVER</code>%0A<b>Machine : </b><code>$os</code>%0A<b>Cores : </b><code>$cores</code>%0A<b>Time : </b><code>$time</code>%0A<b>Branch : </b><code>$CI_BRANCH</code>%0A<b>Top Commit : </b><code>$COMMIT_HEAD</code>"
if ! [ -d "$TC_DIR" ]; then
    echo "Toolchain not found! Cloning to $TC_DIR..."
    tg_post_msg "<code>Toolchain not found! Cloning toolchain</code>"
    if ! git clone -q --depth=1 --single-branch https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86 -b master $TC_DIR; then
        echo "Cloning failed! Aborting..."
        exit 1
    fi
fi
# Colors
NC='\\033[0m'
RED='\\033[0;31m'
LRD='\\033[1;31m'
LGR='\\033[1;32m'
make_defconfig()
{
    START=$(date +"%s")
    echo -e ${LGR} "########### Generating Defconfig ############${NC}"
    make -s ARCH=${ARCH} O=${objdir} ${CONFIG_FILE} -j$(nproc --all)
}
compile()
{
    cd ${kernel_dir}
    echo -e ${LGR} "######### Compiling kernel #########${NC}"
    make -j$(nproc --all) \\
    O=out \\
    ARCH=${ARCH}\\
    CC="ccache clang" \\
    CLANG_TRIPLE="aarch64-linux-gnu-" \\
    CROSS_COMPILE="aarch64-linux-gnu-" \\
    CROSS_COMPILE_ARM32="arm-linux-gnueabi-" \\
    LLVM=1 \\
    LLVM_IAS=1 \\
    2>&1 | tee error.log
}
completion() {
  cd ${objdir}
  COMPILED_IMAGE=arch/arm64/boot/Image.gz-dtb
  COMPILED_DTBO=arch/arm64/boot/dtbo.img
  if [[ -f ${COMPILED_IMAGE} && ${COMPILED_DTBO} ]]; then
    git clone -q https://github.com/kibria5/AnyKernel3 $anykernel
    mv -f $ZIMAGE ${COMPILED_DTBO} $anykernel
    cd $anykernel
    find . -name "*.zip" -type f
    find . -name "*.zip" -type f -delete
    zip -r AnyKernel.zip *
    # Sign the ZIP file using zipsigner-3.0.jar
    curl -sLo zipsigner-3.0.jar https://github.com/Magisk-Modules-Repo/zipsigner/raw/master/bin/zipsigner-3.0-dexed.jar
    java -jar zipsigner-3.0.jar AnyKernel.zip AnyKernel-signed.zip
    mv AnyKernel-signed.zip $zip_name
    mv $anykernel/$zip_name $HOME/$zip_name
    rm -rf $anykernel
    END=$(date +"%s")
    DIFF=$(($END - $START))
    BUILDTIME=$(echo $((${END} - ${START})) | awk '{print int ($1/3600)" Hours:"int(($1/60)%60)"Minutes:"int($1%60)" Seconds"}')
    file_path="$HOME/$zip_name"
    url=$(curl --upload-file "$file_path" https://transfer.sh/"$zip_name")
    zip_size=$(du -h $HOME/$zip_name | awk '{print $1}')
    tg_post_msg "<b>$kernel_name compiled successfully</b>%0A<b>File Name:</b> <code>$zip_name</code>%0A<b>File Size:</b> <code>$zip_size</code>%0A<b>Download Link:</b> <a href='${url}'>Click Here</a>%0A<b>Build Time: $((DIFF / 60)) minute(s) and $((DIFF % 60)) second(s)</b>"
    cd $HOME
    python3 <(curl -s https://gitlab.com/kibria5/kernel_upload/-/raw/main/gh_upload.py)
    echo
    echo -e ${LGR} "############################################"
    echo -e ${LGR} "############# OkThisIsEpic!  ##############"
    echo -e ${LGR} "############################################${NC}"
  else
    tg_post_build "$kernel_dir/error.log" "$CHATID" "Debug Mode Logs"
    tg_post_msg "<code>Compilation failed</code>"
    echo -e ${RED} "############################################"
    echo -e ${RED} "##         This Is Not Epic :'(           ##"
    echo -e ${RED} "############################################${NC}"
  fi
}
make_defconfig
if [ $? -eq 0 ]; then
  tg_post_msg "<code>Defconfig generated successfully</code>"
fi
compile
completion
cd ${kernel_dir}
"""
f.write(s)
f.close()
os.chmod(bashfile, 0o755)
bashcmd=bashfile
for arg in sys.argv[1:]:
  bashcmd += ' '+arg
subprocess.call(bashcmd, shell=True)
