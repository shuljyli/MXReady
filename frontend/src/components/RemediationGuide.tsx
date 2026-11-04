import type { Finding } from "../api/types";
import { CodeSnippet } from "./CodeSnippet";

type Guide = { when: string; before: string; after: string; verify: string; note: string };
const build: Guide = {
  when: "项目将工具链路径或可执行文件写死；先确认目标环境已安装并支持所选工具链。",
  before: 'cuda_home = "/usr/local/cuda"',
  after: 'import os\ncuda_home = os.environ["CUDA_HOME"]  # 由受控构建环境提供',
  verify: 'python -m pip wheel . --no-deps --no-build-isolation -w /tmp/mxready-wheels',
  note: "参数化只消除固定路径。CUDA_HOME 应指向目标工具链公开支持的目录；cu-bridge 的安装与构建入口按对应版本文档配置，不能假设改名后即可兼容。",
};
const device: Guide = {
  when: "默认设备或张量创建位置写死，且算子应跟随输入张量的设备。",
  before: 'out = torch.zeros(x.shape, device="cuda:0")',
  after: 'out = x.new_zeros(x.shape)',
  verify: 'python -m pytest tests -k device',
  note: "检查 shape、dtype 与原实现语义一致。分别覆盖目标 GPU、不同设备编号及必要的 CPU 路径；不是所有 CUDA API 都能按此示例替换。",
};
const native: Guide = {
  when: "发现特定 CUDA 库、头文件、PTX、warp 或内核原语；需要逐项确认目标工具链支持情况。",
  before: 'actual = extension.op(x)  # 只有调用，没有数值回归',
  after: 'actual = extension.op(x)\nexpected = reference_op(x)\ntorch.testing.assert_close(actual, expected, rtol=1e-4, atol=1e-5)',
  verify: 'python -m pytest tests -k parity',
  note: "reference_op 与容差须由项目定义，补齐边界尺寸、dtype、梯度及异常输入。没有通用的一行内核迁移补丁；先验证语义，再评估性能。",
};
const test: Guide = {
  when: "测试跳过或性能数据缺少实际设备执行证据。",
  before: 'start = time.perf_counter()\ny = op(x)\nelapsed = time.perf_counter() - start',
  after: 'torch.cuda.synchronize()\nstart = time.perf_counter()\ny = op(x)\ntorch.cuda.synchronize()\nelapsed = time.perf_counter() - start',
  verify: 'python -m pytest tests -rs',
  note: "示例计时不包含预热和统计，请补齐预热、重复次数、中位数及输入规模。使用目标环境支持的 PyTorch 设备接口；不得把跳过测试记录为通过。",
};
const container: Guide = {
  when: "容器基础镜像或依赖锁定到特定 CUDA 环境。",
  before: 'FROM nvidia/cuda:12.4.1-devel-ubuntu22.04',
  after: 'ARG BASE_IMAGE\nFROM ${BASE_IMAGE}',
  verify: 'docker build --build-arg BASE_IMAGE=<已审核的目标环境镜像及摘要> -t mxready-project .',
  note: "先审核基础镜像、驱动挂载和依赖版本，再构建；占位符必须替换。构建成功不表示容器中 GPU 可用。",
};
const guides: Record<string, Guide> = Object.fromEntries([
  ...["toolchain", "tool", "build", "cmake", "path", "pytorch-extension"].map(key => [key, build]),
  ...["runtime", "architecture"].map(key => [key, device]),
  ...["dependency", "communication", "graph", "header", "intrinsic", "kernel", "library", "ptx", "warp"].map(key => [key, native]),
  ["test", test], ["docker", container],
]);
export function RemediationGuide({ finding }: { finding: Finding }) {
  const guide = guides[finding.category] ?? native;
  return <details className="prose"><summary>整改示例与验证步骤</summary>
    <p>{finding.recommendation}</p><p>适用条件：{guide.when}</p>
    <p>以下是同类问题示例，不是对当前文件的自动补丁；请先复核是否匹配当前命中。</p>
    <h4>修改前</h4><CodeSnippet label={`复制 ${finding.rule_id} 修改前示例`} text={guide.before} />
    <h4>修改后</h4><CodeSnippet label={`复制 ${finding.rule_id} 修改后示例`} text={guide.after} />
    <h4>验证命令</h4><CodeSnippet label={`复制 ${finding.rule_id} 验证示例`} text={guide.verify} />
    <p>{guide.note} 命令仅供在用户控制的环境中人工审阅后运行，网页不会执行。</p>
    <a href="https://docs.pytorch.org/docs/stable/cpp_extension.html" target="_blank" rel="noreferrer">PyTorch 扩展构建说明</a>{" · "}
    <a href="https://docs.pytorch.org/docs/stable/testing.html" target="_blank" rel="noreferrer">PyTorch 数值验证说明</a>
  </details>;
}
