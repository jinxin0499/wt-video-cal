class WtVideoCalError(Exception):
    """Base exception for wt-video-cal."""


class DuplicateVideoError(WtVideoCalError):
    """Raised when duplicate video records are detected."""

    def __init__(
        self,
        duplicates: list[tuple[str, str, list[tuple[str, int]]]],
    ) -> None:
        self.duplicates = duplicates
        creator_count = len({creator for creator, _, _ in duplicates})
        involved_files = sorted(
            {
                file_path
                for _, _, file_orders in duplicates
                for file_path, _ in file_orders
            }
        )
        lines = [
            f"检测到跨文件重复且均有转化订单的视频记录，共 {len(duplicates)} 条：",
            f"  涉及达人: {creator_count} 个",
            f"  涉及文件: {', '.join(involved_files)}",
            "  明细:",
        ]
        for creator, video_id, file_orders in duplicates:
            order_summary = ", ".join(
                f"{file_path}(订单={orders})" for file_path, orders in file_orders
            )
            lines.append(f"    - 达人={creator}, 视频ID={video_id}: {order_summary}")
        super().__init__("\n".join(lines))


class UnknownFormatError(WtVideoCalError):
    """Raised when Excel format cannot be recognized."""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        super().__init__(f"无法识别 Excel 格式: {file_path}")


class ConfigError(WtVideoCalError):
    """Raised for configuration errors."""
