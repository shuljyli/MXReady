import type { ScanReport } from "../api/types";

const base: ScanReport = {
  schema_version: "1.0",
  scan_id: "00000000-0000-0000-0000-000000000001",
  repository: {
    provider: "github",
    owner: "example",
    name: "project",
    url: "https://github.com/example/project",
    commit: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  },
  tool_version: "0.1.0",
  ruleset_version: "1",
  scanned_at: "2026-07-29T00:00:00Z",
  summary: {
    total_count: 0,
    blocker_count: 0,
    warning_count: 0,
    info_count: 0,
    top_blockers: [],
  },
  findings: [],
  migration_checklist: [],
  analysis_warnings: [],
  static_status: "passed",
  verification_status: "not-run",
};

export const staticPassedFixture: ScanReport = base;

export const blockedReportFixture: ScanReport = {
  ...base,
  summary: {
    total_count: 2,
    blocker_count: 1,
    warning_count: 1,
    info_count: 0,
    top_blockers: ["setup.py"],
  },
  static_status: "blocked",
  findings: [
    {
      rule_id: "MXR-TOOLCHAIN-001",
      rule_version: 1,
      severity: "blocker",
      category: "toolchain",
      title: "直接调用 nvcc",
      relative_path: "setup.py",
      line_start: 12,
      line_end: 12,
      evidence: "compiler = 'nvcc'",
      message: "项目直接调用了 nvcc。",
      recommendation: "复核编译器入口，并在沐曦环境中验证 cu-bridge 迁移方式。",
      references: [
        {
          title: "cu-bridge README",
          url: "https://gitee.com/metax-maca/cu-bridge/blob/master/README.md",
        },
      ],
      count: 1,
    },
    {
      rule_id: "MXR-PATH-001",
      rule_version: 1,
      severity: "warning",
      category: "build",
      title: "硬编码 CUDA 路径",
      relative_path: "CMakeLists.txt",
      line_start: 4,
      line_end: 4,
      evidence: "set(CUDA_HOME /usr/local/cuda)",
      message: "构建配置绑定了 CUDA 默认安装目录。",
      recommendation: "把工具链路径改为可配置参数。",
      references: [],
      count: 2,
    },
  ],
  migration_checklist: [
    {
      rule_id: "MXR-TOOLCHAIN-001",
      title: "替换固定编译器入口",
      action: "复核并参数化 CUDA 编译器。",
      affected_files: ["setup.py"],
      completed: false,
    },
  ],
};
