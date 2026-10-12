#!/usr/bin/env python3
"""Generate a Microsoft Word-compatible .doc (Word-flavored HTML) for the
GraminSahay IEEE paper, with all five figures rendered as native VML so they
appear as editable vector block diagrams / charts inside Word.

Revised version:
  * 20 references (was 11)
  * Literature Review written as flowing prose with bold inline thematic
    lead-ins (no sub-headings, no Table I)
  * exactly three Research Gaps
  * Knowledge Sources & Data (datasets) section removed
  * all five figures (Fig. 1-5) retained and embedded
"""

import re

# ---------------------------------------------------------------------------
# 1. Reusable text content
# ---------------------------------------------------------------------------

TITLE = "GraminSahay: An LLM-Powered RAG-Based Rural Welfare and Government Services Navigator"

AUTHORS = [
    ("Mr. S. Lingaiah (Guide, Asst. Professor)", "slingaiah@mlrinstitutions.ac.in", True),
    ("Adigarla Yuva Teja", "yuvateja976@gmail.com", False),
    ("Akhil Vankudoth", "akhilvankudoth58@gmail.com", False),
    ("Adiserla Praneel", "praneeladiserla@gmail.com", False),
]

ABSTRACT = ("Rural India is served by many government welfare schemes&mdash;across agriculture, education, "
    "healthcare, housing, pensions, and employment&mdash;yet a large share of eligible citizens never "
    "see the benefit. The problem is awareness, not supply: people often do not know which schemes fit "
    "them, what documents to bring, how to apply, or why an earlier application failed, and the official "
    "portals expect you to know a scheme&rsquo;s name before you can even search. This paper reviews the "
    "work most relevant to a situation-aware welfare advisor and introduces GraminSahay, a multilingual, "
    "voice-first assistant that lets a citizen describe their situation in ordinary language and then surfaces "
    "the schemes they may qualify for. Under the hood it pairs Retrieval-Augmented Generation (RAG) over "
    "official scheme and policy documents with an eligibility-reasoning layer that labels each scheme eligible, "
    "possibly eligible, not eligible, or missing information; a conflict-detection stage that flags benefits "
    "that cannot be claimed together; and step-by-step guidance for applying. The survey spans RAG and "
    "knowledge-intensive question answering, faithfulness and automated evaluation of RAG, retrieval-augmented "
    "reasoning, multilingual and cross-lingual retrieval, domain adaptation, and the use of large language "
    "models for interpretive support in digital government. From it we draw the research gaps that justify an "
    "explainable rural welfare navigator, and we set out the proposed architecture and methodology.")

KEYWORDS = ("Retrieval-Augmented Generation, Large Language Models, Multilingual Voice AI, Eligibility "
    "Reasoning, Scheme Conflict Detection, Rural Welfare, Public Policy Technology, Indic Speech "
    "Processing, Explainable AI.")

# Sections: (heading, [paragraphs]).  Sub-headings are prefixed with "~".
SECTIONS = [
 ("I. INTRODUCTION", [
   "India runs a wide range of welfare schemes for its rural population, covering agriculture, education, healthcare, housing, and pensions. On paper the coverage is substantial. In practice, many citizens who qualify for a scheme never actually receive its benefit. The problem is mostly one of information, not administration. People often have no idea a relevant scheme even exists; when they do, the eligibility rules are hard to read, the list of required documents is unclear, and a rejected application rarely comes with a usable explanation of what went wrong [1].",
   "Part of the issue is how the official portals are built. They index everything by scheme name, so a citizen has to already know what a scheme is called before the portal is of any use to them. That is backwards. People know their own circumstances; they do not carry around a mental catalogue of scheme names mapped to those circumstances. Language makes this worse: most portals are text-heavy and assume the user can read formal official prose, which leaves out anyone who would rather speak in their regional language [1].",
   "Large language models (LLMs) and Retrieval-Augmented Generation (RAG) give us a way in. In a RAG setup, a retriever first pulls relevant passages from an external document store and a generator then answers using that evidence, so the output is tied to real sources instead of resting only on what the model memorised during training [8]. For welfare, that property matters a great deal: answers have to be correct, they have to be traceable back to an official document, and the underlying corpus has to be easy to refresh when a policy changes. Layer multilingual retrieval and Indic speech on top, and the same system can take a spoken account of someone&rsquo;s situation and reply in the language they actually use.",
   "We present GraminSahay, a multilingual, voice-first welfare navigator built around this idea. A citizen simply states their situation&mdash;say, &ldquo;I am a farmer with a small landholding&rdquo; or &ldquo;my daughter is starting college&rdquo;&mdash;and the system returns the schemes they are likely eligible for, why each decision was reached, a warning if two schemes cannot be claimed together, and the steps needed to apply. This paper concentrates on the research that such a system rests on and the gaps it still has to close.",
   "Why does this matter beyond convenience? Welfare delivery maps onto two of the Sustainable Development Goals&mdash;Goal 1 (No Poverty) and Goal 10 (Reduced Inequalities). A scheme is written to protect a vulnerable household, but it only does so once an eligible person actually claims it. In other words, the hard part of welfare is not drafting the policy; it is the last mile of finding the right scheme, making sense of it, and getting through the application. That is precisely where rural citizens get stuck, and it is where a good assistant can convert policy that already exists into benefit that is actually received&mdash;without touching the schemes themselves.",
   "GraminSahay is shaped by three commitments. The first is that the citizen should never have to name a scheme; the system takes a described situation and works out the candidate schemes itself. The second is explainability&mdash;a bare yes/no verdict is close to useless, so every eligibility decision comes with a plain-language reason tied back to an official source. The third is accessibility: voice and regional-language support are treated as the main way people interact with the system, not as optional extras, because a large part of the intended audience is far more comfortable speaking than reading official documents.",
   "The rest of the paper proceeds as follows. Section II surveys the literature along six strands. Section III sets out the research gaps. The problem statement and motivation appear in Sections IV and V, and Section VI lists the objectives. Section VII compares the existing and proposed systems, Section VIII walks through the methodology, and Section IX gives the solution and architecture. Section X reports the expected results, Section XI looks at future work, and Section XII concludes.",
 ]),
 ("II. LITERATURE REVIEW", [
   "<b>Foundational retrieval-augmented generation.</b> RAG was introduced by Lewis et al. for knowledge-intensive NLP, pairing a pretrained sequence generator with a neural retriever over an external document index [8]. Against a purely parametric baseline it produced answers that were more specific, diverse, and factual, and it improved open-domain question answering, making clear that answer quality can only be as good as retrieval quality [8]. Their experiments ran over a general Wikipedia index, whereas a welfare navigator must retrieve from something far narrower&mdash;a curated set of official scheme guidelines and eligibility rules&mdash;so that more retrieved passages help completeness while widening the surface over which an answer must stay faithful as policy text changes.",
   "<b>Faithfulness and automated evaluation of RAG.</b> A welfare system must never claim an eligibility that the retrieved evidence does not support, so faithfulness is central rather than optional. Filice et al. put forward Answering with Faithfulness (AwF), which checks directly whether an answer is backed by the retrieved passages and shows that stronger faithfulness checks both lift downstream performance and enable principled fallbacks [4]. RAGAs approaches the same problem with reference-free metrics that separately score retrieval relevance, faithfulness, and generation quality, assessing a pipeline without hand-written ground truth for every query [7]. Both help validate eligibility explanations, though automated metrics may not capture whether a legal or policy decision is actually correct, and a study of deployed e-government chatbots confirms that most are evaluated only on effectiveness and usability rather than the correctness and public-value guarantees high-stakes citizen services demand [14].",
   "<b>Retrieval-augmented reasoning.</b> Deciding eligibility is multi-step inference rather than lookup, since occupation, family situation, and location must be checked against several conditions at once. Li et al. survey RAG-reasoning systems that fold multi-step reasoning into retrieval and find that pairing external retrieval with reasoning helps on knowledge-intensive, complex tasks [3], while Self-RAG lets the model decide when to retrieve and then critique both evidence and draft using reflection tokens, improving factuality and citation accuracy [9]. In the same spirit of deciding when to fetch, FLARE looks ahead to the sentence it is about to generate and triggers fresh retrieval when that draft contains low-confidence tokens [18]. Because eligibility is the application of written rules to a citizen&rsquo;s facts, LegalBench is a sobering reference point: across 162 hand-built tasks it shows LLMs handle rule-based legal reasoning unevenly, arguing for grounding every verdict in retrieved policy text rather than parametric judgement [15].",
   "<b>Multilingual and cross-lingual retrieval.</b> Working in English, Telugu, and Hindi puts multilingual retrieval at the heart of the design. Ranaldi et al. weigh translate-the-question RAG against direct multilingual retrieval and report that going direct tends to give better coverage and efficiency, whereas translation can lose coverage [5]; where a translation step is unavoidable, Gala et al.&rsquo;s IndicTrans2 provides open, high-quality translation across all 22 scheduled Indian languages, making a translation-assisted fallback far more viable [16]. Qi et al. show that what RAG retrieves can shift from one language to another, opening cross-lingual inconsistencies [2], and Conneau et al.&rsquo;s XLM-R demonstrates that a single transformer trained on many languages delivers strong cross-lingual transfer with large gains on low-resource languages [17]&mdash;encouraging for Indic text where labelled data is scarce. The practical lesson is to keep query, retrieval, and response languages carefully aligned.",
   "<b>Dense retrieval and domain adaptation.</b> Whether the right scheme document reaches the top of the list comes down to the retriever. The modern line begins with Karpukhin et al.&rsquo;s Dense Passage Retrieval, whose dual-encoder embeddings decisively outperform sparse BM25 baselines [12], while Contriever trains dense retrievers by unsupervised contrastive learning and extends to multilingual retrieval, though it can struggle with specialised government terminology unless tuned [10]. RAFT instead trains an LLM to lean on useful retrieved documents and ignore distractors, reliably improving in-domain performance at the cost of domain-specific training data [6], which is awkward for a policy corpus that keeps moving. For the Indic side specifically, Kakwani et al.&rsquo;s IndicNLPSuite contributes large monolingual corpora, pre-trained models, and the IndicGLUE benchmark [19], giving a concrete starting point for adapting retrievers to Telugu- and Hindi-language policy text.",
   "<b>LLMs for interpretive support in digital government.</b> A systematic review of LLMs for interpretive support in digital-government services finds the field moving from plain question answering toward service navigation and interpretive help, with the clearest gains in efficiency, responsiveness, and accessibility, provided reliability, legal boundaries, responsibility allocation, privacy, and organisational capacity are handled [1]. A separate line of work on context-optimised RAG for local-government welfare subsidies shows concretely that welfare answers can be grounded in local policy documents [11]. On accessibility, a voice-first assistant needs speech in both directions: Radford et al.&rsquo;s Whisper, trained on 680,000 hours of weakly supervised multilingual audio, delivers strong zero-shot transcription across languages and accents [13], while Kumar et al.&rsquo;s Indic-TTS builds synthesis models for major Indian languages [20], together supplying the Indic STT/TTS a rural assistant depends on. Read across these strands, no single prior work understands a situation, retrieves grounded evidence, reasons about eligibility and explains it, catches scheme conflicts, and delivers the result as multilingual voice at once&mdash;the integration gap GraminSahay sets out to fill.",
 ]),
 ("III. RESEARCH GAPS IDENTIFIED", [
   "From the survey above, we draw out three main gaps that the current tools leave open. Each one bundles together several of the shortcomings the literature exposes, and together they define what GraminSahay must address.",
   "<i>Multilingual, Voice-First Accessibility Gap:</i> Existing portals and most prior systems are text-first and effectively single-language, which shuts out a large share of rural users who are far more comfortable speaking in a regional language than reading formal official prose [1]. Even where multilingual components exist, retrieval can behave inconsistently across languages and translation-first pipelines lose coverage [2], [5], while robust Indic speech and shared cross-lingual representations remain under-exploited in the welfare setting [13], [17], [19]. A navigator must therefore accept spoken, regional-language input and respond in the same language, keeping query, retrieval, and response languages aligned.",
   "<i>Explainable, Situation-First Eligibility Gap:</i> Because portals are name-indexed, a citizen who does not already know a scheme&rsquo;s name has nowhere to start, and the single generic page shown to everyone ignores occupation, family circumstances, and location [1]. A bare yes/no verdict is almost useless; what citizens need is situation-first discovery together with an explanation of <i>why</i> a decision was reached, traceable to a trusted source and faithful to the retrieved evidence [4], [9], [15]. Off-the-shelf retrievers and models also stumble on specialised government terminology and on policy text that keeps changing unless they are adapted to the domain [6], [10], [12]. Closing this gap means pairing situation understanding with grounded, multi-step eligibility reasoning that explains itself.",
   "<i>Application-Process Guidance and Conflict-Awareness Gap:</i> Identifying a scheme is only half the task. Existing tools do little to warn that some benefits cannot be held together, leaving the citizen to discover such conflicts the hard way, and they rarely spell out which documents to gather or what the application steps actually are [11], [1]. A useful navigator has to flag mutually exclusive schemes and then carry the citizen through to application with concrete, document-level guidance.",
 ]),
 ("IV. PROBLEM STATEMENT", [
   "The schemes are there, and RAG and LLMs now make grounded question answering practical&mdash;yet rural citizens still cannot dependably find the benefits they are owed, let alone act on them. The portals they are given are name-indexed, generic rather than personal, thin on explanation, blind to conflicts between schemes, and difficult to use for anyone outside the dominant language. What is needed, then, is a navigator that is explainable, situation-aware, multilingual, and voice-first: one that reads a citizen&rsquo;s situation, retrieves the right official information, works out eligibility, warns about conflicting schemes, and sees the person through to application&mdash;none of which should require the citizen to know a scheme&rsquo;s name in advance.",
 ]),
 ("V. MOTIVATION", [
   "What drives this work is a fairly blunt observation: eligible rural citizens miss out on benefits mainly because they cannot find or understand them, not because the benefits do not exist. The usual answers fall short. Manual portal search already assumes you know what you are looking for; generic pages ignore who you actually are; and text-only, single-language interfaces leave out many of the very people the schemes were meant for. Recent research offers the pieces of a better answer. RAG lets us anchor replies in official documents [8]. Retrieval-augmented reasoning handles the multi-step inference that deciding eligibility really involves [3], [9]. Faithfulness-aware generation and automated evaluation keep the answers tethered to the evidence [4], [7]. And multilingual retrieval together with Indic speech makes the whole thing usable by voice in a citizen&rsquo;s own language [2], [5]. Our aim is to bring these pieces together&mdash;situation understanding, RAG retrieval, eligibility reasoning, conflict detection, and multilingual voice&mdash;into one explainable welfare navigator that speaks to SDG 1 (No Poverty) and SDG 10 (Reduced Inequalities).",
 ]),
 ("VI. RESEARCH OBJECTIVES", [
   "The work is organised around six concrete objectives.",
   "<i>Objective 1:</i> Build a voice-first, multilingual front end&mdash;Indic STT/TTS in English, Telugu, and Hindi&mdash;so a citizen can simply say what their situation is.",
   "<i>Objective 2:</i> Turn that free-form description into a structured profile: occupation, family situation, location, and whatever else bears on eligibility.",
   "<i>Objective 3:</i> Stand up a RAG pipeline over the official scheme and policy documents, backed by a vector database for semantic retrieval.",
   "<i>Objective 4:</i> Add a reasoning layer that labels each scheme eligible, possibly eligible, not eligible, or missing information&mdash;and says why.",
   "<i>Objective 5:</i> Detect scheme conflicts, so the citizen is warned when two benefits cannot be claimed together.",
   "<i>Objective 6:</i> Produce step-by-step application guidance for the five pilot categories, listing the documents required and pointing to the official portal or office.",
 ]),
 ("VII. EXISTING SYSTEM AND PROPOSED SYSTEM", [
   "~A. Existing System",
   "As things stand, a citizen has to hunt through government portals and documents by hand, usually needing the scheme&rsquo;s name just to begin. The relevant details are scattered across several places, eligibility and document requirements have to be worked out by reading the fine print, and nobody tailors any of it to the individual. Fig. 1 shows this flow. Its weak points are not subtle: the search is manual, there is almost no personalisation, language is a barrier, and nothing warns you when two schemes conflict.",
   "@FIG_EXISTING@",
   "~B. Proposed System",
   "GraminSahay swaps name-based search for situation-first discovery (Fig. 2). Whatever the citizen says or types becomes a structured profile. From there a RAG layer fetches the relevant passages out of the official-document index, an LLM reasoning layer decides eligibility and explains it, a conflict-detection layer raises a flag when two benefits are mutually exclusive, and a guidance layer lays out what to do next. The answer comes back as multilingual voice in whichever language the citizen chose.",
   "@FIG_PROPOSED@",
 ]),
 ("VIII. PROPOSED METHODOLOGY", [
   "<b>1) Citizen Interaction:</b> Input arrives either by voice (through Indic STT) or as text, with the citizen picking a language&mdash;English, Telugu, or Hindi. A typical opening line is &ldquo;I am a farmer with a small landholding.&rdquo;",
   "<b>2) Profile Understanding:</b> From that free-form sentence the system pulls out a structured profile: occupation, family situation, location, and any other detail that happens to matter.",
   "<b>3) RAG Retrieval:</b> The profile and the query are embedded together and used to fetch the top-<i>k</i> passages from a vector database built over the scheme guidelines, eligibility rules, and policy documents.",
   "<b>4) Eligibility Reasoning:</b> An LLM weighs each candidate scheme against the retrieved evidence and tags it eligible, possibly eligible, not eligible, or missing information&mdash;and where something is missing, it says what else it would need to know.",
   "<b>5) Scheme-Conflict Detection:</b> The chosen schemes are checked against one another, and the citizen is warned whenever two benefits cannot legally be held together.",
   "<b>6) Application Guidance:</b> Once a scheme is picked, the system explains why it fits, lists the documents needed, spells out the application steps, and links through to the official portal or office.",
   "<b>7) Multilingual Voice Output:</b> Finally the reply is spoken back through Indic TTS in whichever language the citizen selected.",
   "<b>8) Evaluation:</b> We will judge the pipeline on three fronts&mdash;retrieval relevance, answer faithfulness, and eligibility-classification quality&mdash;using reference-free RAG metrics [7] alongside faithfulness evaluation [4]. Concretely, retrieval is scored with Recall@k and mean reciprocal rank over labelled situation&ndash;scheme pairs; classification with per-class precision, recall, and macro-F1 across the four labels; and faithfulness as the fraction of justifications that the retrieved passages fully back up. On top of the automated numbers, a small panel of domain reviewers will rate how clear and how correct the explanations are.",
   "Two concerns run across the whole design. One is keeping the data fresh: schemes and thresholds move, so the corpus is versioned and re-indexed on a schedule, and every answer notes the document version it leaned on. The other is privacy: we keep the citizen profile deliberately thin&mdash;only the attributes eligibility actually needs&mdash;and nothing sensitive is held past the session unless the citizen opts in, which lines up with the governance conditions the digital-government literature stresses [1].",
 ]),
 ("IX. PROPOSED SOLUTION AND SYSTEM ARCHITECTURE", [
   "The layered architecture is drawn in Fig. 3. Work moves top to bottom&mdash;citizen interaction, profile understanding, RAG retrieval, eligibility reasoning, conflict detection, application guidance&mdash;and ends in multilingual voice output. The band at the bottom names the stack we intend to use: a Flutter / React Native front end, a FastAPI / Node.js back end, PostgreSQL for user and application data, a multilingual LLM with RAG doing the reasoning and generation, a vector database handling document retrieval, and Indic STT/TTS for the voice side.",
   "@FIGURE@",
 ]),
 ("X. EXPECTED RESULTS", [
   "Since this is a proposal rather than a finished build, the figures below are what we <i>expect</i> once the system is implemented and evaluated. Think of them as targets to aim at; the real numbers will replace them after the experiments are run.",
   "~A. Expected Performance (Tabular)",
   "Table I lays out the performance we anticipate across the five pilot categories, reported as retrieval Recall@5, answer faithfulness [4], [7], eligibility-classification accuracy, and macro-F1.",
   "@TABLE2@",
   "Table II contrasts GraminSahay with the existing manual approach on the qualitative capabilities identified as research gaps in Section III.",
   "@TABLE3@",
   "~B. Expected Performance (Graphs)",
   "Fig. 4 plots the expected classification accuracy for each category. Fig. 5 traces what happens to retrieval Recall@k and answer faithfulness as we pull back more passages: a bigger <i>k</i> lifts recall but tends to water down faithfulness, which is why we settle on roughly <i>k</i> = 5 as a sensible middle ground.",
   "@FIG_BAR@",
   "@FIG_LINE@",
   "~C. Discussion of Expected Outcomes",
   "Taken together, Tables I and II and Figs. 4 and 5 describe how we want the system to behave. The healthcare and education numbers in Table I are kept deliberately modest: eligibility there hinges on several conditions at once&mdash;income bands, institution type, age&mdash;which is simply harder to get right than, say, a pension scheme with fairly uniform rules. Table II, meanwhile, is about the difference a citizen would actually feel: the manual process offers no situation-first discovery, no explainable eligibility, and no conflict detection, while the proposed system offers all three. Fig. 5 puts the main tension on the table&mdash;more passages mean higher recall but a smaller fraction of the answer that is strictly backed by evidence&mdash;and that is what pushes us toward k &asymp; 5. We treat these figures as acceptance thresholds rather than aspirations: a configuration passes only if it hits the tabulated accuracy and faithfulness <i>and</i> keeps end-to-end latency low enough to feel interactive over voice.",
 ]),
 ("XI. FUTURE ENHANCEMENTS", [
   "Once the prototype is working, there are several directions we would like to take it.",
   "&bull; <b>Broader coverage:</b> Push past the five pilot categories and past Telangana&mdash;to more states and to central schemes&mdash;keeping the policy corpus continuously up to date.",
   "&bull; <b>More languages:</b> Grow the Indic STT/TTS and multilingual retrieval beyond English, Telugu, and Hindi into further regional languages and dialects.",
   "&bull; <b>Document-aware applications:</b> Allow citizens to upload or photograph documents such as land records or ration cards, so the system can check eligibility conditions automatically and even pre-fill parts of the form.",
   "&bull; <b>Offline / low-bandwidth mode:</b> Run lightweight models on-device and cache scheme data, so the navigator still works where connectivity is poor.",
   "&bull; <b>Live policy integration:</b> Wire the system directly into government portal APIs for real-time scheme updates, application submission, and status tracking.",
   "&bull; <b>Explainability and trust:</b> Attach source citations and confidence scores to every answer, and route borderline eligibility cases to a human for review.",
   "&bull; <b>Accessibility:</b> Reach citizens without smartphones by adding IVR / telephone and WhatsApp channels.",
 ]),
 ("XII. CONCLUSION", [
   "This paper surveyed the work most relevant to a situation-aware rural welfare navigator and used it to pin down the research gaps that GraminSahay is meant to close. A few things come through clearly from that survey: RAG keeps generation anchored in authoritative documents; faithfulness evaluation and retrieval-augmented reasoning together make multi-step eligibility inference trustworthy; multilingual retrieval and Indic speech open the door to voice access in regional languages; and domain adaptation is what makes any of this hold up on specialised policy text. GraminSahay stitches these together&mdash;situation understanding, RAG retrieval, eligibility reasoning, conflict detection, and multilingual voice. What we expect to end up with is an explainable, accessible assistant that helps a rural citizen find the right government support, grasp whether they qualify, see what information is still missing, and move toward applying&mdash;all without having to know a scheme&rsquo;s name to begin with. The next steps are to widen the system past the five pilot categories and the starting set of languages, and to report real, measured numbers for retrieval and eligibility performance.",
 ]),
]

REFERENCES = [
 "X. Zhang, Z. Ma, Y. Ma, and I. Ismail, &ldquo;Large Language Models for Interpretive Support in Digital Government Service Systems: A Systematic Review,&rdquo; <i>Systems</i>, vol. 14, no. 7, art. 823, 2026.",
 "J. Qi, R. Fern&aacute;ndez, and A. Bisazza, &ldquo;On the Consistency of Multilingual Context Utilization in Retrieval-Augmented Generation,&rdquo; in <i>Proc. 5th Workshop on Multilingual Representation Learning (MRL 2025)</i>, 2025.",
 "Y. Li et al., &ldquo;A Survey of RAG-Reasoning Systems in Large Language Models,&rdquo; in <i>Findings of ACL: EMNLP 2025</i>, pp. 12120&ndash;12145, 2025.",
 "S. Filice, E. Haramaty, G. Horowitz, Z. Karnin, L. Lewin-Eytan, and A. Shtoff, &ldquo;Generate but Verify: Answering with Faithfulness in RAG-based Question Answering,&rdquo; in <i>Proc. IJCNLP-AACL 2025</i>, pp. 1017&ndash;1037, 2025.",
 "L. Ranaldi, B. Haddow, and A. Birch, &ldquo;Multilingual Retrieval-Augmented Generation for Knowledge-Intensive Question Answering Task,&rdquo; in <i>Findings of EACL 2026</i>, 2026.",
 "T. Zhang, S. G. Patil, N. Jain, S. Shen, M. Zaharia, I. Stoica, and J. E. Gonzalez, &ldquo;RAFT: Adapting Language Model to Domain-Specific RAG,&rdquo; in <i>Proc. Conf. on Language Modeling (COLM)</i>, 2024. arXiv:2403.10131.",
 "S. Es, J. James, L. Espinosa-Anke, and S. Schockaert, &ldquo;RAGAs: Automated Evaluation of Retrieval Augmented Generation,&rdquo; in <i>Proc. 18th Conf. of the European Chapter of the ACL (EACL): System Demonstrations</i>, 2024, pp. 150&ndash;158.",
 "P. Lewis et al., &ldquo;Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks,&rdquo; in <i>Advances in Neural Information Processing Systems (NeurIPS)</i>, 2020.",
 "A. Asai, Z. Wu, Y. Wang, A. Sil, and H. Hajishirzi, &ldquo;Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection,&rdquo; in <i>Proc. Int. Conf. on Learning Representations (ICLR)</i>, 2024.",
 "G. Izacard, M. Caron, L. Hosseini, S. Riedel, P. Bojanowski, A. Joulin, and E. Grave, &ldquo;Unsupervised Dense Information Retrieval with Contrastive Learning,&rdquo; <i>Transactions on Machine Learning Research (TMLR)</i>, 2022.",
 "M. G. Kumar and S. Rao, &ldquo;Context-Optimized Retrieval Augmented Generation for Local Government Welfare Subsidies,&rdquo; in <i>Proc. IEEE Int. Conf. on Systems, Man, and Cybernetics (SMC)</i>, 2025, pp. 1105&ndash;1112.",
 "V. Karpukhin, B. O&#287;uz, S. Min, P. Lewis, L. Wu, S. Edunov, D. Chen, and W. Yih, &ldquo;Dense Passage Retrieval for Open-Domain Question Answering,&rdquo; in <i>Proc. 2020 Conf. on Empirical Methods in Natural Language Processing (EMNLP)</i>, 2020, pp. 6769&ndash;6781.",
 "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, and I. Sutskever, &ldquo;Robust Speech Recognition via Large-Scale Weak Supervision,&rdquo; in <i>Proc. 40th Int. Conf. on Machine Learning (ICML)</i>, 2023, pp. 28492&ndash;28518.",
 "M. E. Cort&eacute;s-Cediel, A. Segura-Tinoco, I. Cantador, and M. P. Rodr&iacute;guez Bol&iacute;var, &ldquo;Trends and Challenges of E-Government Chatbots: Advances in Exploring Open Government Data and Citizen Participation Content,&rdquo; <i>Government Information Quarterly</i>, 2023.",
 "N. Guha, J. Nyarko, D. E. Ho, C. R&eacute;, A. Chohlas-Wood, A. Peters, B. Waldon, D. N. Rockmore, D. Zambrano, et al., &ldquo;LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models,&rdquo; in <i>Advances in Neural Information Processing Systems (NeurIPS)</i>, 2023.",
 "J. Gala, P. A. Chitale, R. AK, V. Gumma, S. Doddapaneni, A. Kumar, et al., &ldquo;IndicTrans2: Towards High-Quality and Accessible Machine Translation Models for all 22 Scheduled Indian Languages,&rdquo; <i>Transactions on Machine Learning Research (TMLR)</i>, 2023.",
 "A. Conneau, K. Khandelwal, N. Goyal, V. Chaudhary, G. Wenzek, F. Guzm&aacute;n, E. Grave, M. Ott, L. Zettlemoyer, and V. Stoyanov, &ldquo;Unsupervised Cross-lingual Representation Learning at Scale,&rdquo; in <i>Proc. 58th Annual Meeting of the ACL</i>, 2020, pp. 8440&ndash;8451.",
 "Z. Jiang, F. Xu, L. Gao, Z. Sun, Q. Liu, J. Dwivedi-Yu, Y. Yang, J. Callan, and G. Neubig, &ldquo;Active Retrieval Augmented Generation,&rdquo; in <i>Proc. 2023 Conf. on Empirical Methods in Natural Language Processing (EMNLP)</i>, 2023, pp. 7969&ndash;7992.",
 "D. Kakwani, A. Kunchukuttan, S. Golla, G. N. C., A. Bhattacharyya, M. M. Khapra, and P. Kumar, &ldquo;IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages,&rdquo; in <i>Findings of the ACL: EMNLP 2020</i>, 2020, pp. 4948&ndash;4961.",
 "G. Kumar, P. S. Virk, J. Jayakumar, et al., &ldquo;Towards Building Text-to-Speech Systems for the Next Billion Users (Indic-TTS),&rdquo; in <i>Proc. IEEE Int. Conf. on Acoustics, Speech and Signal Processing (ICASSP)</i>, 2023. arXiv:2211.09536.",
]

# ---------------------------------------------------------------------------
# 2. VML figures (native Word vector; hand-drawn block style)
# ---------------------------------------------------------------------------

def rbox(x,y,w,h,fill,stroke,text,fs=9,bold=False,italic=False,dash=False):
    style = f"position:absolute;left:{x}pt;top:{y}pt;width:{w}pt;height:{h}pt"
    dashattr = ' dashstyle="dash"' if dash else ''
    b = 'bold' if bold else 'normal'
    it = 'italic' if italic else 'normal'
    return (f'<v:roundrect style="{style}" arcsize="0.12" fillcolor="{fill}" '
            f'strokecolor="{stroke}" strokeweight="1.2pt"{dashattr}>'
            f'<v:textbox inset="2pt,1pt,2pt,1pt" style="v-text-anchor:middle">'
            f'<center style="font-family:Segoe UI,Arial;font-size:{fs}pt;'
            f'font-weight:{b};font-style:{it};color:#222">{text}</center>'
            f'</v:textbox></v:roundrect>')

def band(x,y,w,h,fill,stroke,title,dash=False):
    style=f"position:absolute;left:{x}pt;top:{y}pt;width:{w}pt;height:{h}pt"
    dashattr=' dashstyle="dash"' if dash else ''
    return (f'<v:roundrect style="{style}" arcsize="0.06" fillcolor="{fill}" '
            f'strokecolor="{stroke}" strokeweight="1.4pt"{dashattr}>'
            f'<v:textbox inset="4pt,2pt,2pt,2pt" style="v-text-anchor:top">'
            f'<p style="font-family:Segoe UI,Arial;font-size:9.5pt;font-weight:bold;'
            f'color:#333;margin:0">{title}</p></v:textbox></v:roundrect>')

def vline(x1,y1,x2,y2):
    return (f'<v:line from="{x1}pt,{y1}pt" to="{x2}pt,{y2}pt" strokecolor="#333" '
            f'strokeweight="1.6pt"><v:stroke endarrow="block"/></v:line>')

def build_vml():
    s = ['<div style="text-align:center">',
         '<!--[if gte vml 1]>',
         '<v:group xmlns:v="urn:schemas-microsoft-com:vml" coordsize="430,560" '
         'coordorigin="0,0" style="width:430pt;height:560pt">']
    s.append(band(5,5,420,52,"#DAE8FC","#6C8EBF","1 &#8212; Citizen Interaction Layer"))
    s.append(rbox(12,24,95,28,"#FFFFFF","#6C8EBF","&#127897; Voice (Indic STT)",8))
    s.append(rbox(112,24,80,28,"#FFFFFF","#6C8EBF","&#9000; Text Input",8))
    s.append(rbox(197,24,105,28,"#FFFFFF","#6C8EBF","&#127760; English+Telugu+Hindi",8))
    s.append(rbox(307,24,112,28,"#FFF2CC","#D6B656","&quot;I am a farmer with a small landholding.&quot;",7.5,italic=True))

    s.append(band(5,75,420,46,"#D5E8D4","#82B366","2 &#8212; Profile Understanding Layer"))
    s.append(rbox(12,94,95,22,"#FFFFFF","#82B366","Occupation",8))
    s.append(rbox(112,94,95,22,"#FFFFFF","#82B366","Family Situation",8))
    s.append(rbox(212,94,95,22,"#FFFFFF","#82B366","Location",8))
    s.append(rbox(312,94,107,22,"#FFFFFF","#82B366","Other Details",8))

    s.append(band(5,139,420,56,"#FFE6CC","#D79B00","3 &#8212; RAG Retrieval Layer"))
    s.append(rbox(12,158,120,32,"#FFFFFF","#D79B00","&#128218; Scheme Guidelines &amp; Eligibility Rules",8))
    s.append(rbox(140,158,130,32,"#FFFFFF","#D79B00","&#128451; Vector Database (semantic search)",8))
    s.append(rbox(278,158,140,32,"#FFFFFF","#D79B00","&#128269; Embedding + Top-k Retrieval",8))

    s.append(band(5,213,420,50,"#E1D5E7","#9673A6","4 &#8212; Eligibility Reasoning Layer (LLM)"))
    s.append(rbox(12,232,95,26,"#D5E8D4","#82B366","&#9989; Eligible",8))
    s.append(rbox(112,232,95,26,"#FFF2CC","#D6B656","&#10067; Possibly Eligible",8))
    s.append(rbox(212,232,95,26,"#F8CECC","#B85450","&#10060; Not Eligible",8))
    s.append(rbox(312,232,107,26,"#DAE8FC","#6C8EBF","&#8505; Missing Info",8))

    s.append(band(5,281,420,46,"#F8CECC","#B85450","5 &#8212; Scheme Conflict Detection Layer"))
    s.append(rbox(12,300,125,22,"#FFFFFF","#B85450","&#9888; Identify mutually exclusive schemes",8))
    s.append(rbox(142,300,125,22,"#FFFFFF","#B85450","Warn: ineligible combinations",8))
    s.append(rbox(272,300,147,22,"#FFF2CC","#D6B656","&quot;Scheme A &amp; B cannot be claimed together.&quot;",7.5,italic=True))

    s.append(band(5,345,420,50,"#DAE8FC","#6C8EBF","6 &#8212; Application Guidance Layer"))
    s.append(rbox(12,364,95,26,"#FFFFFF","#6C8EBF","Why scheme is relevant",8))
    s.append(rbox(112,364,95,26,"#FFFFFF","#6C8EBF","&#128203; Required documents",8))
    s.append(rbox(212,364,95,26,"#FFFFFF","#6C8EBF","&#128228; Step-by-step process",8))
    s.append(rbox(312,364,107,26,"#FFFFFF","#6C8EBF","&#128279; Official portal / office",8))

    s.append(rbox(110,410,210,34,"#D5E8D4","#82B366","7 &#8212; Multilingual Voice Output (Indic TTS) &#128266; &#8212; response in selected language",8,bold=True))

    s.append(band(5,462,420,56,"#F5F5F5","#666666","Technology Stack",dash=True))
    s.append(rbox(10,482,78,30,"#FFFFFF","#666","Frontend Flutter / RN",7.5))
    s.append(rbox(92,482,80,30,"#FFFFFF","#666","Backend FastAPI / Node",7.5))
    s.append(rbox(176,482,70,30,"#FFFFFF","#666","DB PostgreSQL",7.5))
    s.append(rbox(250,482,88,30,"#FFFFFF","#666","AI/LLM LLM + RAG",7.5))
    s.append(rbox(342,482,78,30,"#FFFFFF","#666","Voice Indic STT+TTS",7.5))

    for y1,y2 in [(57,75),(121,139),(195,213),(263,281),(327,345),(395,410)]:
        s.append(vline(215,y1,215,y2))

    s.append('</v:group><![endif]-->')
    s.append('</div>')
    return "".join(s)

def vml_open(w,h):
    return ('<div style="text-align:center"><!--[if gte vml 1]>'
            f'<v:group xmlns:v="urn:schemas-microsoft-com:vml" coordsize="{w},{h}" '
            f'coordorigin="0,0" style="width:{w}pt;height:{h}pt">')
def vml_close():
    return '</v:group><![endif]--></div>'

def build_vml_existing():
    s=[vml_open(430,120)]
    xs=[5,95,190,285,375]; ws=[75,88,88,88,50]
    labels=["Citizen","Search Portal (by name)","Find Scheme","Check Eligibility (manual)","Apply"]
    for x,w,lb in zip(xs,ws,labels):
        s.append(rbox(x,15,w,30,"#F0F0F0","#888",lb,8))
    for i in range(4):
        x1=xs[i]+ws[i]; x2=xs[i+1]
        s.append(vline(x1,30,x2,30))
    s.append(f'<v:rect style="position:absolute;left:5pt;top:60pt;width:420pt;height:48pt" '
             f'fillcolor="#FFF4F4" strokecolor="#B85450" strokeweight="1pt">'
             f'<v:textbox inset="4pt,2pt,4pt,2pt"><p style="font-family:Segoe UI;font-size:8pt;'
             f'color:#9a3b3b;margin:0"><b>Limitations:</b> must know scheme name &#183; no personalization '
             f'&#183; language barriers &#183; info scattered &#183; manual eligibility interpretation '
             f'&#183; no conflict detection</p></v:textbox></v:rect>')
    s.append(vml_close())
    return "".join(s)

def build_vml_proposed():
    s=[vml_open(430,230)]
    r1=[(5,"1. Voice/Text Input","#DAE8FC","#6C8EBF"),
        (112,"2. Profile Build","#D5E8D4","#82B366"),
        (219,"3. RAG Retrieval","#FFE6CC","#D79B00"),
        (326,"4. Eligibility Reasoning (LLM)","#E1D5E7","#9673A6")]
    for x,lb,f,st in r1:
        s.append(rbox(x,10,100,46,f,st,lb,8,bold=True))
    s.append(vline(105,33,112,33)); s.append(vline(212,33,219,33)); s.append(vline(319,33,326,33))
    s.append(vline(376,56,376,80))
    s.append(vline(376,80,269,80)); s.append(vline(269,80,269,95))
    r2=[(219,"5. Conflict Detection","#F8CECC","#B85450"),
        (112,"6. Application Guidance","#DAE8FC","#6C8EBF"),
        (5,"7. Voice Output (TTS)","#D5E8D4","#82B366")]
    for x,lb,f,st in r2:
        s.append(rbox(x,95,100,46,f,st,lb,8,bold=True))
    s.append(vline(219,118,212,118)); s.append(vline(112,118,105,118))
    s.append(rbox(90,170,250,40,"#FFF2CC","#D6B656",
        "Explainable, situation-aware welfare navigation &#8212; no prior scheme name needed",8,bold=True))
    s.append(vline(55,141,55,190)); s.append(vline(55,190,88,190))
    s.append(vml_close())
    return "".join(s)

def build_vml_bar():
    s=[vml_open(300,210)]
    data=[("Agri",91,"#4472C4"),("Edu",88,"#5B9BD5"),("Health",86,"#70AD47"),
          ("Housing",89,"#ED7D31"),("Pension",93,"#9673A6")]
    base=170; scale=1.5
    s.append(f'<v:line from="30pt,{base}pt" to="285pt,{base}pt" strokecolor="#333" strokeweight="1pt"/>')
    s.append(f'<v:line from="30pt,20pt" to="30pt,{base}pt" strokecolor="#333" strokeweight="1pt"/>')
    x=45
    for name,val,col in data:
        h=val*scale; y=base-h
        s.append(f'<v:rect style="position:absolute;left:{x}pt;top:{y}pt;width:34pt;height:{h}pt" '
                 f'fillcolor="{col}" strokecolor="#333"/>')
        s.append(f'<v:shape style="position:absolute;left:{x-3}pt;top:{y-14}pt;width:40pt;height:12pt" '
                 f'filled="f" stroked="f"><v:textbox inset="0,0,0,0"><center '
                 f'style="font-family:Segoe UI;font-size:7pt">{val}</center></v:textbox></v:shape>')
        s.append(f'<v:shape style="position:absolute;left:{x-5}pt;top:{base+2}pt;width:44pt;height:12pt" '
                 f'filled="f" stroked="f"><v:textbox inset="0,0,0,0"><center '
                 f'style="font-family:Segoe UI;font-size:7pt">{name}</center></v:textbox></v:shape>')
        x+=48
    s.append(f'<v:shape style="position:absolute;left:40pt;top:4pt;width:220pt;height:14pt" '
             f'filled="f" stroked="f"><v:textbox inset="0,0,0,0"><center '
             f'style="font-family:Segoe UI;font-size:8pt;font-weight:bold;color:#1F3864">'
             f'Expected Accuracy by Category (%)</center></v:textbox></v:shape>')
    s.append(vml_close())
    return "".join(s)

def build_vml_line():
    s=[vml_open(300,210)]
    base=170; left=35; w=240
    s.append(f'<v:line from="{left}pt,{base}pt" to="{left+w}pt,{base}pt" strokecolor="#333" strokeweight="1pt"/>')
    s.append(f'<v:line from="{left}pt,20pt" to="{left}pt,{base}pt" strokecolor="#333" strokeweight="1pt"/>')
    ks=list(range(1,11))
    recall=[0.55,0.68,0.76,0.81,0.84,0.86,0.87,0.88,0.885,0.89]
    faith =[0.93,0.925,0.915,0.90,0.885,0.865,0.845,0.825,0.805,0.78]
    def pt(k,v):
        x=left+(k-1)*(w/9.0); y=base-v*150
        return f"{x:.0f}pt,{y:.0f}pt"
    s.append('<v:polyline points="'+' '.join(pt(k,v) for k,v in zip(ks,recall))+
             '" filled="f" strokecolor="#4472C4" strokeweight="2pt"/>')
    s.append('<v:polyline points="'+' '.join(pt(k,v) for k,v in zip(ks,faith))+
             '" filled="f" strokecolor="#70AD47" strokeweight="2pt" dashstyle="dash"/>')
    s.append(f'<v:shape style="position:absolute;left:40pt;top:4pt;width:230pt;height:14pt" '
             f'filled="f" stroked="f"><v:textbox inset="0,0,0,0"><center '
             f'style="font-family:Segoe UI;font-size:8pt;font-weight:bold;color:#1F3864">'
             f'Recall@k (solid) vs Faithfulness (dashed)</center></v:textbox></v:shape>')
    s.append(f'<v:shape style="position:absolute;left:{left}pt;top:{base+2}pt;width:{w}pt;height:12pt" '
             f'filled="f" stroked="f"><v:textbox inset="0,0,0,0"><center '
             f'style="font-family:Segoe UI;font-size:7pt">Top-k  (1 &#8594; 10)</center></v:textbox></v:shape>')
    s.append(vml_close())
    return "".join(s)

# ---------------------------------------------------------------------------
# 3. Assemble the Word HTML document
# ---------------------------------------------------------------------------

def fcap(txt):
    return (f'<p class=cap style="text-align:center;font-size:8pt;'
            f'font-weight:bold;margin:3pt 0 8pt">{txt}</p>')

def table2():
    rows=[("Welfare Category","Recall@5","Faithfulness","Eligibility Acc. (%)","Macro-F1"),
          ("Agriculture","0.90","0.92","91","0.89"),
          ("Education","0.88","0.90","88","0.86"),
          ("Healthcare","0.86","0.89","86","0.84"),
          ("Housing","0.89","0.91","89","0.87"),
          ("Pensions","0.92","0.93","93","0.90"),
          ("Overall (avg.)","0.89","0.91","89.4","0.87")]
    out=['<p class=cap style="text-align:center;font-weight:bold;margin:6pt 0 2pt">'
         'Table I.&nbsp;&nbsp;Expected Performance Across Welfare Categories</p>'
         '<table class=lit>']
    for i,r in enumerate(rows):
        bold=' style="font-weight:bold"' if (i==len(rows)-1) else ''
        if i==0:
            out.append('<tr>'+''.join(f'<td class=th>{c}</td>' for c in r)+'</tr>')
        else:
            out.append('<tr>'+''.join(f'<td class=td{bold}>{c}</td>' for c in r)+'</tr>')
    out.append('</table>')
    return "".join(out)

def table3():
    rows=[("Capability","Existing (manual portal)","GraminSahay (proposed)"),
          ("Situation-first discovery (no scheme name needed)","No","Yes"),
          ("Personalized to profile","No","Yes"),
          ("Explainable eligibility","Limited","Yes (4-way + reasons)"),
          ("Scheme-conflict detection","No","Yes"),
          ("Multilingual voice access","No","Yes (Eng+Telugu+Hindi)"),
          ("Step-by-step application guidance","Partial","Yes")]
    out=['<p class=cap style="text-align:center;font-weight:bold;margin:6pt 0 2pt">'
         'Table II.&nbsp;&nbsp;Expected Capability Comparison</p>'
         '<table class=lit>']
    for i,r in enumerate(rows):
        if i==0:
            out.append('<tr>'+''.join(f'<td class=th>{c}</td>' for c in r)+'</tr>')
        else:
            out.append('<tr>'+''.join(f'<td class=td>{c}</td>' for c in r)+'</tr>')
    out.append('</table>')
    return "".join(out)

def para(txt):
    if txt == "@FIGURE@":
        return build_vml() + fcap("Fig. 3.&nbsp;&nbsp;Layered system flow and architecture of GraminSahay.")
    if txt == "@FIG_EXISTING@":
        return build_vml_existing() + fcap("Fig. 1.&nbsp;&nbsp;Existing system &mdash; manual welfare scheme lookup.")
    if txt == "@FIG_PROPOSED@":
        return build_vml_proposed() + fcap("Fig. 2.&nbsp;&nbsp;Proposed system &mdash; GraminSahay situation-first flow.")
    if txt == "@FIG_BAR@":
        return build_vml_bar() + fcap("Fig. 4.&nbsp;&nbsp;Expected eligibility-classification accuracy by category.")
    if txt == "@FIG_LINE@":
        return build_vml_line() + fcap("Fig. 5.&nbsp;&nbsp;Expected retrieval quality vs. top-k passages retrieved.")
    if txt == "@TABLE2@":
        return table2()
    if txt == "@TABLE3@":
        return table3()
    if txt.startswith("~"):
        return f'<p class=sub>{txt[1:]}</p>'
    return f'<p class=body>{txt}</p>'

def build():
    out=[]
    out.append('''<html xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:w="urn:schemas-microsoft-com:office:word"
 xmlns="http://www.w3.org/TR/REC-html40"><head>
<meta charset="utf-8"><title>GraminSahay IEEE Paper</title>
<!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View>
<w:Zoom>100</w:Zoom></w:WordDocument></xml><![endif]-->
<style>
@page Section1 { size:595.3pt 841.9pt; margin:50pt 42pt 50pt 42pt;
  mso-columns:2 even 18pt; }
div.Section1 { page:Section1; }
body { font-family:"Times New Roman",serif; font-size:9.6pt; text-align:justify; }
h1.title { font-size:17pt; font-weight:bold; text-align:center; margin:0 0 8pt;
  mso-element:span-all; }
table.authtbl { width:100%; mso-element:span-all; border:none; }
table.authtbl td { text-align:center; font-size:9pt; border:none; vertical-align:top; }
.aname { font-weight:bold; font-size:10pt; }
.ph { color:#000000; }
p.abs { font-weight:bold; font-style:italic; margin:0 0 6pt; text-align:justify; }
p.body { margin:0 0 6pt; text-indent:10pt; }
p.sub  { margin:6pt 0 2pt; font-weight:bold; font-style:italic; }
p.sec  { text-align:center; font-weight:bold; margin:10pt 0 4pt;
  font-variant:small-caps; font-size:10pt; }
p.cap  { }
table.lit { border-collapse:collapse; width:100%; mso-element:span-all;
  font-size:7.6pt; margin-bottom:8pt; }
table.lit td { border:0.75pt solid #000; padding:2pt 3pt; vertical-align:top; }
td.th { background:#d9d9d9; font-weight:bold; text-align:center; }
p.ref  { margin:0 0 3pt; text-indent:-13pt; mso-text-indent-alt:-13pt;
  padding-left:13pt; font-size:8.4pt; }
</style></head><body><div class=Section1>''')

    out.append(f'<h1 class=title>{TITLE}</h1>')
    out.append('<table class=authtbl><tr>')
    for name,email,isph in AUTHORS:
        out.append(f'<td><span class=aname>{name}</span><br>Dept. of CSE<br>'
                   f'MLR Institute of Technology<br>Hyderabad, India<br>{email}</td>')
    out.append('</tr></table><br clear=all>')

    out.append(f'<p class=abs><i>Abstract&mdash;</i>{ABSTRACT}</p>')
    out.append(f'<p class=abs><i>Keywords&mdash;</i>{KEYWORDS}</p>')

    for i,(head,paras) in enumerate(SECTIONS):
        out.append(f'<p class=sec>{head}</p>')
        for p in paras:
            out.append(para(p))

    out.append('<p class=sec>REFERENCES</p>')
    for i,r in enumerate(REFERENCES,1):
        out.append(f'<p class=ref>[{i}]&nbsp;&nbsp;{r}</p>')

    out.append('</div></body></html>')
    return "".join(out)

if __name__ == "__main__":
    doc = build()
    with open('GraminSahay_IEEE_Paper.doc','w',encoding='utf-8') as f:
        f.write(doc)
    print("Wrote GraminSahay_IEEE_Paper.doc:", len(doc), "bytes")
    leftover=re.findall(r'@[A-Z0-9_]+@', doc)
    assert not leftover, "leftover markers: %s"%leftover
    print("VML groups:", doc.count('<v:group'))
    print("Tables:", doc.count('<table class=lit>'))
    print("Fig captions:", len(re.findall(r'Fig\. \d', doc)))
    print("References:", doc.count('<p class=ref>'))
    print("Emails ok:", all(e in doc for e in ['yuvateja976','akhilvankudoth58','praneeladiserla']))
