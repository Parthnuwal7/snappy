"""Built-in starter templates (mock skeletons) available to every firm."""
BUILTIN_TEMPLATES = [
    {"key": "wakalatnama", "name": "Wakalatnama (starter)", "category": "wakalatnama",
     "body": "<h2 style=\"text-align:center\">WAKALATNAMA</h2>"
             "<p>IN THE COURT OF {{court}}</p>"
             "<p>{{petitioner}} &hellip;Petitioner</p><p>versus</p><p>{{respondent}} &hellip;Respondent</p>"
             "<p>I/We, the above-named {{client}}, do hereby appoint and retain my/our advocate to "
             "appear, act and plead on my/our behalf in the above matter ({{case_number}}).</p>"
             "<p>Dated: {{date}}</p>"},
    {"key": "legal_notice", "name": "Legal notice (starter)", "category": "notice",
     "body": "<p>Date: {{date}}</p><p>To,<br>{{respondent}}</p>"
             "<p><strong>Subject: Legal notice on behalf of {{client}}</strong></p>"
             "<p>Under instructions from and on behalf of my client {{client}}, I hereby serve you "
             "with the following notice in the matter of {{matter}} &hellip;</p>"
             "<p>Yours faithfully,</p><p>Advocate for {{client}}</p>"},
]
