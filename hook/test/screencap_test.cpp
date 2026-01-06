/**
 * MSA 后台截图测试程序
 *
 * 功能：
 * 1. 使用自定义控制器连接游戏
 * 2. 通过 MAA API 执行后台截图
 * 3. 将截图保存为 PNG 文件
 *
 * 验收标准：
 * - 游戏窗口可以在后台（被其他窗口遮挡）
 * - 截图成功并保存为文件
 * - 截图内容正确（不是黑屏或错误图像）
 */

#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "controller/controller.h"
#include "MaaFramework/MaaAPI.h"

// 日志输出
void Log(const char* format, ...) {
    va_list args;
    va_start(args, format);
    printf("[截图测试] ");
    vprintf(format, args);
    printf("\n");
    va_end(args);
}

void LogError(const char* format, ...) {
    va_list args;
    va_start(args, format);
    printf("[截图测试 错误] ");
    vprintf(format, args);
    printf(" (错误码: %lu)\n", GetLastError());
    va_end(args);
}

// 保存 BGRA 数据为 BMP 文件（简单实现，不依赖外部库）
bool SaveBMP(const char* filename, const uint8_t* data, int width, int height) {
    // BMP 文件头
    #pragma pack(push, 1)
    struct BMPFileHeader {
        uint16_t type;          // 'BM'
        uint32_t size;          // 文件大小
        uint16_t reserved1;
        uint16_t reserved2;
        uint32_t offset;        // 像素数据偏移
    };

    struct BMPInfoHeader {
        uint32_t size;          // 信息头大小
        int32_t width;
        int32_t height;
        uint16_t planes;
        uint16_t bitCount;
        uint32_t compression;
        uint32_t sizeImage;
        int32_t xPelsPerMeter;
        int32_t yPelsPerMeter;
        uint32_t clrUsed;
        uint32_t clrImportant;
    };
    #pragma pack(pop)

    FILE* fp = fopen(filename, "wb");
    if (!fp) {
        return false;
    }

    int rowSize = ((width * 4 + 3) / 4) * 4;  // 4 字节对齐
    int imageSize = rowSize * height;

    BMPFileHeader fileHeader = {};
    fileHeader.type = 0x4D42;  // 'BM'
    fileHeader.size = sizeof(BMPFileHeader) + sizeof(BMPInfoHeader) + imageSize;
    fileHeader.offset = sizeof(BMPFileHeader) + sizeof(BMPInfoHeader);

    BMPInfoHeader infoHeader = {};
    infoHeader.size = sizeof(BMPInfoHeader);
    infoHeader.width = width;
    infoHeader.height = -height;  // 负值表示从上到下
    infoHeader.planes = 1;
    infoHeader.bitCount = 32;
    infoHeader.compression = 0;
    infoHeader.sizeImage = imageSize;

    fwrite(&fileHeader, sizeof(fileHeader), 1, fp);
    fwrite(&infoHeader, sizeof(infoHeader), 1, fp);

    // 写入像素数据
    for (int y = 0; y < height; ++y) {
        fwrite(data + y * width * 4, width * 4, 1, fp);
        // 填充对齐字节
        int padding = rowSize - width * 4;
        if (padding > 0) {
            uint8_t zeros[4] = {0};
            fwrite(zeros, padding, 1, fp);
        }
    }

    fclose(fp);
    return true;
}

// 事件回调
void EventCallback(void* handle, const char* message, const char* details_json, void* trans_arg) {
    Log("事件: %s", message);
    if (details_json && strlen(details_json) > 0 && strcmp(details_json, "{}") != 0) {
        Log("详情: %s", details_json);
    }
}

int main() {
    // 设置控制台编码为 UTF-8
    SetConsoleOutputCP(65001);

    printf("========================================\n");
    printf("    MSA 后台截图测试程序\n");
    printf("    第二阶段验收\n");
    printf("========================================\n\n");

    // 检查 Windows Graphics Capture 支持
    Log("检查系统支持...");
    // 注意：Screencap_IsSupported() 需要在 WinRT 初始化后调用
    // 这里我们直接尝试创建控制器

    // 创建控制器上下文
    Log("创建控制器...");
    MsaControllerContext* ctx = MsaController_Create(NULL);  // NULL 表示自动查找游戏窗口
    if (!ctx) {
        LogError("创建控制器上下文失败");
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }

    // 创建 MAA 控制器
    MaaController* controller = MaaCustomControllerCreate(
        MsaController_GetCallbacks(ctx),
        MsaController_GetTransArg(ctx)
    );

    if (!controller) {
        LogError("创建 MAA 控制器失败");
        MsaController_Destroy(ctx);
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }

    // 添加事件回调
    MaaControllerAddSink(controller, EventCallback, NULL);

    // 连接
    Log("正在连接游戏...");
    MaaCtrlId connId = MaaControllerPostConnection(controller);
    MaaStatus status = MaaControllerWait(controller, connId);

    if (status != MaaStatus_Succeeded) {
        LogError("连接失败，状态: %d", status);
        MaaControllerDestroy(controller);
        MsaController_Destroy(ctx);
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }

    Log("连接成功！");

    // 获取 UUID
    MaaStringBuffer* uuidBuffer = MaaStringBufferCreate();
    if (MaaControllerGetUuid(controller, uuidBuffer)) {
        Log("控制器 UUID: %s", MaaStringBufferGet(uuidBuffer));
    }
    MaaStringBufferDestroy(uuidBuffer);

    // 交互式测试
    printf("\n========================================\n");
    printf("    测试菜单\n");
    printf("========================================\n");
    printf("1. 执行截图并保存\n");
    printf("2. 连续截图测试（5次）\n");
    printf("3. 退出\n");
    printf("========================================\n");

    while (1) {
        printf("\n请选择操作 (1-3): ");
        int choice;
        if (scanf("%d", &choice) != 1) {
            while (getchar() != '\n');
            continue;
        }

        switch (choice) {
        case 1: {
            // 单次截图
            Log("正在截图...");

            MaaCtrlId screencapId = MaaControllerPostScreencap(controller);
            status = MaaControllerWait(controller, screencapId);

            if (status != MaaStatus_Succeeded) {
                LogError("截图失败，状态: %d", status);
                break;
            }

            // 获取截图数据
            MaaImageBuffer* imageBuffer = MaaImageBufferCreate();
            if (!MaaControllerCachedImage(controller, imageBuffer)) {
                LogError("获取截图数据失败");
                MaaImageBufferDestroy(imageBuffer);
                break;
            }

            int width = MaaImageBufferWidth(imageBuffer);
            int height = MaaImageBufferHeight(imageBuffer);
            void* rawData = MaaImageBufferGetRawData(imageBuffer);

            Log("截图成功！尺寸: %d x %d", width, height);

            // 生成文件名
            time_t now = time(NULL);
            struct tm* t = localtime(&now);
            char filename[256];
            snprintf(filename, sizeof(filename), "screenshot_%04d%02d%02d_%02d%02d%02d.bmp",
                t->tm_year + 1900, t->tm_mon + 1, t->tm_mday,
                t->tm_hour, t->tm_min, t->tm_sec);

            // 保存为 BMP
            if (SaveBMP(filename, (const uint8_t*)rawData, width, height)) {
                Log("截图已保存: %s", filename);
            } else {
                LogError("保存截图失败");
            }

            MaaImageBufferDestroy(imageBuffer);
            break;
        }

        case 2: {
            // 连续截图测试
            Log("开始连续截图测试（5次）...");

            LARGE_INTEGER freq, start, end;
            QueryPerformanceFrequency(&freq);

            for (int i = 0; i < 5; ++i) {
                QueryPerformanceCounter(&start);

                MaaCtrlId screencapId = MaaControllerPostScreencap(controller);
                status = MaaControllerWait(controller, screencapId);

                QueryPerformanceCounter(&end);

                double elapsed = (double)(end.QuadPart - start.QuadPart) / freq.QuadPart * 1000.0;

                if (status == MaaStatus_Succeeded) {
                    MaaImageBuffer* imageBuffer = MaaImageBufferCreate();
                    if (MaaControllerCachedImage(controller, imageBuffer)) {
                        int width = MaaImageBufferWidth(imageBuffer);
                        int height = MaaImageBufferHeight(imageBuffer);
                        Log("第 %d 次截图成功，尺寸: %d x %d，耗时: %.2f ms", i + 1, width, height, elapsed);
                    }
                    MaaImageBufferDestroy(imageBuffer);
                } else {
                    LogError("第 %d 次截图失败", i + 1);
                }

                Sleep(100);  // 间隔 100ms
            }

            Log("连续截图测试完成");
            break;
        }

        case 3:
            goto cleanup;

        default:
            printf("无效选择，请重试\n");
            break;
        }
    }

cleanup:
    // 清理
    Log("正在清理...");
    MaaControllerDestroy(controller);
    MsaController_Destroy(ctx);

    Log("测试程序结束");
    printf("\n按任意键退出...");
    getchar();
    getchar();

    return 0;
}
