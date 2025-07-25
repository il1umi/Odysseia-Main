# --- 辅助函数 ---
import asyncio
import re
from typing import List, Optional

from discord import Thread, Guild, ui

from src.license.constants import *
from src.license.database import *


def _format_links_in_text(text: str) -> str:
    """
    一个辅助函数，用于查找文本中的【裸露URL】并将其转换为Markdown链接。
    它会智能地处理 Discord 链接以规避其渲染BUG，并美化其他链接的显示文本。
    """
    if not text:
        return text

    # 正则表达式，用于匹配裸露的URL
    url_pattern = re.compile(r'(?<!\]\()(https?://[^\s<>()]+)')

    def replacer(match: re.Match) -> str:
        """
        一个自定义的替换函数，用于 re.sub。
        """
        url = match.group(0)  # 获取完整的URL，例如 "https://example.com"

        # 检查是否是 Discord 消息链接
        if "discord.com/" in url:
            # 对于 Discord 链接，使用固定的友好文本
            link_text = "「点击查看 Discord 链接内容」"
            return f"[{link_text}]({url})"
        else:
            # 对于其他链接，移除协议头作为显示文本
            link_text = re.sub(r'^https?://', '', url)
            # 移除尾部的斜杠，让显示更干净
            if link_text.endswith('/'):
                link_text = link_text[:-1]
            return f"[{link_text}]({url})"

    # 使用 re.sub 并传入我们的自定义替换函数
    return url_pattern.sub(replacer, text)


def build_settings_embed(config: LicenseConfig) -> discord.Embed:
    """
    工厂函数：创建一个包含所有配置项及其详细解释的设置面板Embed。
    """
    description_parts = []

    # 1. 机器人总开关
    enabled_emoji = "✅ 启用" if config.bot_enabled else "❌ 禁用"
    description_parts.append(f"**机器人总开关**: {enabled_emoji}")
    description_parts.append(
        "> 控制机器人在你发新帖时是否会自动出现。关闭后，你需要使用 `/内容授权 打开面板` 手动召唤我。"
    )
    description_parts.append("---")

    # 2. 自动发布默认协议
    auto_post_emoji = "✅ 启用" if config.auto_post else "❌ 禁用"
    description_parts.append(f"**自动发布默认协议**: {auto_post_emoji}")
    description_parts.append(
        "> 启用后，当机器人出现时，将直接尝试发布你的默认协议，而不会显示一系列交互按钮让你选择。"
    )
    description_parts.append("---")

    # 3. 发布前二次确认
    confirm_emoji = "✅ 启用" if config.require_confirmation else "❌ 禁用"
    description_parts.append(f"**发布前二次确认**: {confirm_emoji}")
    description_parts.append(
        "> 启用后，在发布任何协议前（包括自动发布），都会先让你预览并点击确认。"
    )

    description_parts.append("\n完成后，点击下方的“关闭面板”即可。（不关也行，保存是实时的，就是不够优雅，懂吧？）")

    # 使用我们现有的标准助手Embed框架来创建
    return create_helper_embed(
        title="⚙️ 机器人设置详解",
        description="\n".join(description_parts),
        color=discord.Color.blurple()
    )


def create_helper_embed(title: str, description: str, color: discord.Color = discord.Color.blue()) -> discord.Embed:
    """
    工厂函数：创建一个标准的、带有助手签名的交互面板Embed。
    这确保了所有中间状态的交互消息都能被正确识别和清理。
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text=build_footer_text(SIGNATURE_HELPER))
    return embed


async def safe_delete_original_response(interaction: discord.Interaction, sleep_time: int = 0) -> None:
    if sleep_time > 0:
        await asyncio.sleep(sleep_time)
    try:
        await interaction.delete_original_response()
    except discord.NotFound:
        pass  # 如果用户在此期间关闭了，也无妨


async def get_member_async_thread(thread: Thread, user_id: int) -> Member | None:
    return thread.guild.get_member(user_id) or await thread.guild.fetch_member(user_id)


async def get_member_async_guild(guild: Guild, user_id: int) -> Member | None:
    return guild.get_member(user_id) or await guild.fetch_member(user_id)


def get_member(thread: Thread, user_id: int) -> discord.Member:
    return thread.guild.get_member(user_id)


def build_footer_text(signature: str) -> str:
    """
    统一的页脚文本构建器。
    它会自动附加统一的“宣传语”。

    Args:
        signature: 标识此 Embed 类型的签名，
                   如 HELPER_SIGNATURE 或 LICENSE_SIGNATURE。

    Returns:
        一个格式化好的、符合全新标准的页脚字符串。
    """
    cmd_name = ACTIVE_COMMAND_CONFIG["group"]["name"]
    cmd_name_panel = ACTIVE_COMMAND_CONFIG["panel"]["name"]
    return f"{signature} | 如果按钮失效(服务器重启、超时)，请使用 `/{cmd_name} {cmd_name_panel}`"


async def safe_defer(interaction: discord.Interaction):
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True)


def get_available_cc_licenses() -> dict:
    """
    此函数现在不再执行过滤，始终返回所有CC协议。
    过滤逻辑移至前端视图中，以便更好地向用户展示禁用状态。
    """
    return CC_LICENSES


async def do_simple_owner_id_interaction_check(owner_id: int, interaction: discord.Interaction) -> bool:
    if interaction.user.id != owner_id:
        await interaction.response.send_message("❌ 你无法操作这个菜单。", ephemeral=True)
        return False
    return True


def get_item_by_id(view: ui.View, custom_id: str) -> Optional[ui.Item]:
    """通过 custom_id 在视图的子组件中查找一个项目。"""
    for item in view.children:
        if hasattr(item, 'custom_id') and item.custom_id == custom_id:
            return item
    return None


def get_available_software_licenses() -> dict:
    """返回所有可用的软件协议。"""
    return SOFTWARE_LICENSES


# 为了代码整洁，将附录文本定义为常量
_EFFECTIVENESS_RULES_TEXT = (
    f"👑 **作者说了算**：作者在任何地方的**亲口声明**或**操作**，其效力**永远高于**本协议。{SIGNATURE_HELPER}仅提供方便工具，作者保留所有的解释权。\n"
    f"🤝 **关于单独授权**：无论本协议如何规定，从**作者**得到的**单独授权**可以不受本协议限制。\n"
    f"🔄 **默认覆盖**：为方便作者管理并避免信息混淆，若无作者额外声明，发布新协议将自动取代**由{SIGNATURE_HELPER}发布的**旧协议。\n"
    "> **⚠️ 请注意**：从法律上讲，对那些在旧协议有效期内**已经获取**作品的人，其授权通常不可撤销。尽管如此，我们倡导所有用户尊重作者的意愿。"
)
_CC_DISCLAIMER_TEXT = (
    "**⚠️ 关于CC协议的特别说明**\n"
    "如果创作者在任何地方对本协议添加了**额外规则**，那么这份协议就不再是**标准CC协议**了。\n"
    "它会变成一份**“长得像CC协议的自定义协议”**，其中的CC链接仅用于解释基础条款。"
)


def build_license_embeds(
        config: LicenseConfig,
        author: discord.Member,
        commercial_use_allowed: bool,
        *,
        title_override: Optional[str] = None,
        footer_override: Optional[str] = None,
        include_appendix: bool = True
) -> List[discord.Embed]:
    """
    根据给定的配置对象和作者信息，构建一个支持完整Markdown附加条款的美观Embed。
    """
    saved_details = config.license_details.copy()  # 使用副本以防修改原始配置对象
    license_type = saved_details.get("type", "custom")
    is_cc_license = license_type in CC_LICENSES
    is_software_license = license_type in SOFTWARE_LICENSES

    warning_message = None  # 用于存储将要显示的警告信息

    # --- 策略校验与自动降级逻辑 ---
    if not commercial_use_allowed:
        # 1. 对自定义协议，强制覆盖商业条款
        if license_type == "custom":
            saved_details["commercial"] = "禁止"

        # 2. 对CC协议，检查冲突并执行降级
        elif license_type in CC_LICENSES and "NC" not in license_type:
            original_license = license_type
            # 尝试找到对应的NC版本
            # 例如: "CC BY 4.0" -> "CC BY-NC 4.0"
            #       "CC BY-SA 4.0" -> "CC BY-NC-SA 4.0"
            potential_nc_version = license_type.replace("CC BY", "CC BY-NC")

            if potential_nc_version in CC_LICENSES:
                # 成功找到可降级的版本
                license_type = potential_nc_version
                saved_details["type"] = license_type
                is_cc_license = True  # 保持同步
            else:
                # 如果找不到（例如对于 CC0 这种未来可能添加的），则降级为自定义
                license_type = "custom"
                saved_details["type"] = "custom"
                saved_details["commercial"] = "禁止"
                is_cc_license = False  # 已降级为自定义

            # 准备警告信息
            warning_message = (
                f"**⚠️ 协议已自动调整**\n"
                f"由于本服务器禁止商业用途，您误选择的协议 **{original_license}** "
                f"已被自动调整为 **{license_type}**。"
            )

    # --- Embed 构建流程 ---
    display_details = saved_details
    # 如果降级了，就强制使用新协议的数据
    if is_cc_license:
        display_details.update(CC_LICENSES[license_type])
    elif is_software_license:
        display_details.update(SOFTWARE_LICENSES[license_type])

    # --- 智能替换占位符 ---
    # 定义在不同情况下的替换文本
    placeholder_replacement = ""
    if is_cc_license:
        # 如果是标准的CC协议，用具体的协议名称替换
        placeholder_replacement = license_type
    else:
        # 如果是自定义协议（包括从CC降级而来的），使用通用短语
        placeholder_replacement = "相同的条款"

    # 遍历核心条款，执行替换
    for key in ["reproduce", "derive", "commercial"]:
        if key in display_details and isinstance(display_details[key], str):
            display_details[key] = display_details[key].format(license_type=placeholder_replacement)

    description_parts = []
    description_parts.append(f"**发布者: ** {author.mention}")

    if is_cc_license:
        description_parts.append(f"本内容采用 **[{license_type}]({display_details['url']})** 国际许可协议进行许可。")
    elif is_software_license:
        description_parts.append(f"本项目采用 **[{license_type}]({display_details['url']})** 开源许可证。")

    # 如果存在警告信息，将其添加到描述中
    if warning_message:
        description_parts.append(f"\n> {warning_message}")  # 使用引用块使其更醒目

    # 准备一个列表来存储最终要发送的所有Embed
    embeds_to_send: List[discord.Embed] = []

    # 3. 创建 Embed 并组合描述
    main_embed_title = title_override or "📜 内容授权协议"
    main_embed = discord.Embed(
        title=main_embed_title,
        description="\n".join(description_parts) if description_parts else None,
        color=discord.Color.gold() if not warning_message else discord.Color.orange()  # 警告时使用不同颜色
    )

    # 使用 set_author 来展示作者信息
    # 这会在 Embed 的最顶部显示作者的头像和名字
    main_embed.set_author(name=f"由 {author.display_name} ({author.name}) 发布", icon_url=author.display_avatar.url)

    # 4. 添加结构化的核心条款字段
    # --- 根据协议类型（内容/软件）填充不同的字段 ---
    if is_software_license:
        main_embed.add_field(name="📄 协议类型", value=f"**{license_type}** (软件)", inline=False)
        main_embed.add_field(name="✒️ 版权归属", value=_format_links_in_text(display_details.get("attribution", "未设置")), inline=False)
        main_embed.add_field(name="📜 核心条款", value=display_details["full_text"], inline=False)
    else:  # 自定义或CC协议
        if is_cc_license:
            main_embed.add_field(name="📄 协议类型", value=f"**{license_type}**", inline=False)
        else:
            main_embed.add_field(name="📄 协议类型", value="**自定义协议**", inline=False)
        main_embed.add_field(name="✒️ 作者署名", value=_format_links_in_text(display_details.get("attribution", "未设置")), inline=False)
        main_embed.add_field(name="🔁 二次传播", value=_format_links_in_text(display_details.get("reproduce", "未设置")), inline=True)
        main_embed.add_field(name="🎨 二次创作", value=_format_links_in_text(display_details.get("derive", "未设置")), inline=True)
        main_embed.add_field(name="💰 商业用途", value=_format_links_in_text(display_details.get("commercial", "未设置")), inline=True)

    # 附加条款
    if not is_cc_license:
        notes = display_details.get("notes")
        if notes and notes.strip() and notes != "无":
            # 注意：add_field 的 value 不支持复杂的 Markdown，但简单的链接可以
            main_embed.add_field(name="📝 附加条款 (如无另外声明，其效力范围同本协议)", value=_format_links_in_text(notes), inline=False)

    # 添加宽度拉伸器，保证主Embed宽度
    # `\uu2800` 是盲文空格
    stretcher_value = ' ' + '\u2800' * 30

    # 设置页脚
    cmd_name = ACTIVE_COMMAND_CONFIG["group"]["name"]
    footer_text = footer_override or SIGNATURE_LICENSE+f" | 在自己的帖子里，使用 `/{cmd_name}` 来使用我吧！"
    main_embed.set_footer(text=footer_text + stretcher_value)

    embeds_to_send.append(main_embed)

    # --- 按需构建附录并返回 ---
    # 添加“协议生效规则”字段
    if include_appendix:
        appendix_description_parts = [_EFFECTIVENESS_RULES_TEXT]
        if is_cc_license:
            appendix_description_parts.append("\n\n" + _CC_DISCLAIMER_TEXT)

        appendix_embed = discord.Embed(
            title="⚖️ 协议生效规则",
            description="\n".join(appendix_description_parts),
            color=discord.Color.light_grey()
        )

        # # 为附录Embed也设置页脚
        # # 如果主页脚被覆盖了，附录也应该用被覆盖的那个，以保持一致
        # # 否则，附录也使用标准的协议签名页脚
        # appendix_footer_text = footer_override or build_footer_text(SIGNATURE_LICENSE)
        # # 这里不需要使用魔法拉伸，因为本来就够长
        # appendix_embed.set_footer(text='-# '+appendix_footer_text)

        embeds_to_send.append(appendix_embed)

    # --- 构建附言Embed (如果存在) ---
    personal_statement: str = display_details.get("personal_statement")
    # 附言
    if personal_statement and personal_statement.strip() and personal_statement != "无":
        postscript_embed = discord.Embed(
            # 使用 title 来展示标题，更醒目
            title="📣 附言 (无法律效力)",
            # description 用来展示内容，支持完整的Markdown
            description=personal_statement,
            color=discord.Color.blue()
        )
        # 保持页脚一致性
        # postscript_embed.set_footer(text=footer_text + stretcher_value)
        embeds_to_send.append(postscript_embed)

    return embeds_to_send
