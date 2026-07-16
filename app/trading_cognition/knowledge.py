from __future__ import annotations

from dataclasses import asdict, dataclass


SOURCE_NAME = "尼克｜交易性格（公开内容蒸馏）"
SOURCE_VERSION = "2026-07-14"
SOURCE_NOTICE = (
    "基于114条抖音公开作品与105条可用口播逐字稿归纳；内容用于交易认知创作，"
    "不代表创作者的全部观点，也不构成投资建议。"
)


@dataclass(frozen=True)
class KnowledgeCard:
    id: str
    title: str
    keywords: tuple[str, ...]
    belief: str
    reasoning: tuple[str, ...]
    action_rule: str
    source_titles: tuple[str, ...]

    def to_public_dict(self) -> dict:
        data = asdict(self)
        data.pop("keywords", None)
        return data

    def to_prompt_context(self) -> str:
        reasoning = "；".join(self.reasoning)
        sources = "；".join(self.source_titles)
        return (
            f"[{self.title}]\n"
            f"核心判断：{self.belief}\n"
            f"论证路径：{reasoning}\n"
            f"行动规则：{self.action_rule}\n"
            f"公开内容依据：{sources}"
        )


KNOWLEDGE_CARDS: tuple[KnowledgeCard, ...] = (
    KnowledgeCard(
        id="stop_loss",
        title="止损不是看空，是给错误划边界",
        keywords=("止损", "砍仓", "割肉", "扛单", "反弹", "回本", "认错", "风险边界"),
        belief="止损的作用不是证明方向判断正确，而是在市场证明判断失效时，把损失限制在计划内。",
        reasoning=(
            "人不肯止损，常常不是因为还有新证据，而是在等市场原谅自己",
            "单笔行情不可控，但每笔最多亏多少、何时退出可以事先定义",
            "没有退出标准，亏损就会从一次交易判断升级为对账户生存的威胁",
        ),
        action_rule="进场前写清失效条件、最大可承受损失和退出动作；条件触发后执行，不在场内临时改规则。",
        source_titles=(
            "你理解的交易‘确定性’是什么？",
            "到底怎么理解‘心不死，道不生’‘知行合一’",
            "如果你儿子要和你学交易……",
        ),
    ),
    KnowledgeCard(
        id="survival_first",
        title="第一关不是赚钱，是不死",
        keywords=("新手", "生存", "爆仓", "本金", "活下来", "赚钱", "安全", "第一关"),
        belief="初学者的第一目标不是扩大利润，而是避免一次不可恢复的损失，保留继续训练的资格。",
        reasoning=(
            "本金越大不会自动修复亏钱的技能，只会放大同一种错误",
            "能长期留在场内，才有足够样本验证系统和认识自己",
            "把安全放在利润之前，单笔决策才不会被暴富目标绑架",
        ),
        action_rule="先限制单笔风险和总仓位，再谈收益目标；任何可能让账户失去下一次机会的动作都应被否决。",
        source_titles=("如果你儿子要和你学交易……", "和隐世交易者聊天，才懂交易真正靠什么"),
    ),
    KnowledgeCard(
        id="control_circle",
        title="确定性不在预测，在可控规则",
        keywords=("确定性", "预测", "胜率", "行情", "圣杯", "可控", "规则", "猜对"),
        belief="市场方向和单笔盈亏没有确定性，真正可控的是入场条件、仓位、止损和执行过程。",
        reasoning=(
            "把确定性放在行情里，会不断寻找永远正确的指标或老师",
            "把确定性收回规则里，关注点会从猜对变成是否按计划做对",
            "市场分析可以参与决策，但不能替代风险边界",
        ),
        action_rule="复盘时先问‘我是否按规则执行’，再问‘这笔是否赚钱’，把过程质量和随机结果分开。",
        source_titles=("你理解的交易‘确定性’是什么？", "真正的交易系统，是从你身上长出来的～"),
    ),
    KnowledgeCard(
        id="loss_to_rule",
        title="亏损只有换成规则，才算学费",
        keywords=("亏损", "学费", "失败", "犯错", "教训", "代价", "白亏", "总结"),
        belief="亏损本身不会让人进步；只有还原原因、提取规律并改变下一次动作，成本才转化成经验。",
        reasoning=(
            "计划内亏损是系统成本，违规亏损暴露的是规则或执行漏洞",
            "只看盈亏会把运气误当能力，也会把正常回撤误当失败",
            "同一种错误重复发生，说明所谓复盘没有进入行动层",
        ),
        action_rule="每笔亏损标记为计划内或违规；违规项必须生成一条可检查的新规则，并在下一次交易前复述。",
        source_titles=("90%的人不会交易复盘，因为少做了这三件事", "明白了什么道理，交易水平突飞猛涨？"),
    ),
    KnowledgeCard(
        id="knowing_doing",
        title="知道止损和真的止损，隔着人性",
        keywords=("知行合一", "执行", "执行力", "情绪", "恐惧", "贪婪", "管不住手", "犹豫"),
        belief="知道规则不等于能执行；真实交易会触发侥幸、损失厌恶和自我证明，让人临时背叛计划。",
        reasoning=(
            "亏损扩大时，人会把退出理解成承认自己失败",
            "连续亏损后，即使标准再次触发，也可能因恐惧而跳过",
            "执行问题不能只靠意志，需要把动作写清并减少临场解释空间",
        ),
        action_rule="把触发条件写成可复盘的具体句子，并记录每次规则触发后是执行、犹豫还是跳过。",
        source_titles=("到底怎么理解‘心不死，道不生’‘知行合一’", "交易走不出来，看这四大心法～"),
    ),
    KnowledgeCard(
        id="review",
        title="复盘不是重播后悔，是修补规则",
        keywords=("复盘", "记录", "交易日志", "总结", "后悔", "还原现场", "规律", "改进"),
        belief="有效复盘不从盈亏数字开始，而是还原决策现场，区分系统成本、执行错误和偶然结果。",
        reasoning=(
            "只回看结果容易产生后见之明，误以为当时本该知道",
            "还原当时看到的信息，才能判断决策质量",
            "规律必须落实为下一次可检查的动作，否则只是情绪安慰",
        ),
        action_rule="按‘还原现场—提取规律—变成行动’三步复盘，并连续观察同一问题是否重复。",
        source_titles=("90%的人不会交易复盘，因为少做了这三件事",),
    ),
    KnowledgeCard(
        id="position_risk",
        title="仓位不是利润按钮，是生存阀门",
        keywords=("仓位", "重仓", "轻仓", "加仓", "杠杆", "风险", "回撤", "满仓"),
        belief="仓位决定判断错误时要付出的代价；再好的观点也不能替代风险预算。",
        reasoning=(
            "重仓会放大波动，也会放大恐惧和临场改规则的冲动",
            "轻仓不是为了亏得慢，而是为了让错误仍然可恢复",
            "加仓应由预先定义的条件触发，而不是用来拯救浮亏",
        ),
        action_rule="先确定账户可承受风险，再反推仓位；不因确信、焦虑或想回本临时放大风险。",
        source_titles=("为什么说散户高频交易必死？", "如果你儿子要和你学交易……"),
    ),
    KnowledgeCard(
        id="system_fit",
        title="交易系统不能只抄答案，要适配自己",
        keywords=("交易系统", "策略", "方法", "照抄", "性格", "适配", "量化", "正期望"),
        belief="规则可以借鉴，但成熟系统必须经过自己的样本验证，并与时间、能力和性格相适配。",
        reasoning=(
            "机器能稳定执行策略，却不能把负期望策略变成黄金",
            "照抄他人的盈利路径，可能是在用自己的短板硬扛市场",
            "越复杂的参数越可能只是拟合过去，而非抓住稳定逻辑",
        ),
        action_rule="用自己的交易记录验证规则，优先保留逻辑清楚、能长期执行且样本外仍有效的部分。",
        source_titles=("真正的交易系统，是从你身上长出来的～", "交易者们吵来吵去，其实都在舒适区打转"),
    ),
)


CARD_BY_ID = {card.id: card for card in KNOWLEDGE_CARDS}
