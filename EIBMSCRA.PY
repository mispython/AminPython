
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            branch = parse_int(line[1:4])
            brchcd = line[5:8].strip()
            item = Branch(branch=branch, brchcd=brchcd)
            by_branch[branch] = item
            by_brchcd[brchcd] = item

    return by_branch, by_brchcd


def read_hr_branch(path: Path) -> dict[int, HrBranch]:
    rows: dict[int, HrBranch] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            staff = parse_int(line[4:9])
            branch = parse_int(line[68:71])
            brchcd = line[71:74].strip()
            if 2 <= branch <= 267:
                rows[staff] = HrBranch(staff=staff, branch=branch, brchcd=brchcd)
    return rows


def read_hr_ho(path: Path) -> dict[int, HrHo]:
    rows: dict[int, HrHo] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            staff = parse_int(line[4:9])
            hoe = line[71:86].strip()
            rows[staff] = HrHo(staff=staff, hoe=hoe)
    return rows


def read_card_files(paths: Iterable[Path]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                acctno = parse_int(line[0:11])
                typec = int(str(acctno)[:5])
                if typec not in {3301, 3302, 3305, 3306, 3308, 3309, 5503, 5504}:
                    continue

                opnmm = parse_int(line[13:15])
                opnyr = parse_int(line[15:17])
                seco = line[560:572].strip()
                if not ((opnyr == 6 and opnmm > 8) or opnyr >= 7):
                    continue
                if not (1 < len(seco) < 6):
                    continue

                staff = parse_int(seco)
                if not (1 < staff < 99999):
                    continue

                if typec == 3309:
                    rows.append(
                        SrsRecord(
                            staff=staff,
                            product="CARD",
                            ncore="X",
                            acctno=acctno,
                            c1cnt=1,
                        )
                    )
                else:
                    rows.append(
                        SrsRecord(
                            staff=staff,
                            product="CARD",
                            ncore="C",
                            acctno=acctno,
                            c2cnt=1,
                        )
                    )

    return rows


def read_dep_files(paths: Iterable[Path], branch_by_number: dict[int, Branch]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                acctno = parse_int(line[1:11])
                primoff = parse_int(line[49:54])
                secnoff = parse_int(line[55:60])
                xcore = line[60:61]
                ytdbals = parse_sas_number(line[75:89], implied_decimals=2)
                nummth = parse_int(line[89:91])
                branch_no = parse_int(line[96:99])
                branch = branch_by_number.get(branch_no)
                if branch is None:
                    continue

                product = ""
                if 1000000000 <= acctno <= 1999999999 or 7000000000 <= acctno <= 7999999999:
                    product = "FIXED DEPOSITS"
                elif 3000000000 <= acctno <= 3999999999:
                    product = "CURRENT ACCOUNT"
                elif 4000000000 <= acctno <= 4999999999 or 6000000000 <= acctno <= 6999999999:
                    product = "SAVING ACCOUNT"

                if not product or nummth == 0:
                    continue

                ytdbal = round(ytdbals / nummth)

                if primoff and xcore == " ":
                    rows.append(
                        SrsRecord(
                            staff=primoff,
                            product=product,
                            ncore="X",
                            branch=branch.branch,
                            brchcd=branch.brchcd,
                            tag="DEPO",
                            acctno=acctno,
                            c1cnt=1,
                            c1bal=ytdbal,
                        )
                    )

                staff = secnoff or primoff
                if staff and xcore in {"C", "N"}:
                    if xcore == "C":
                        rows.append(
                            SrsRecord(
                                staff=staff,
                                product=product,
                                ncore="C",
                                branch=branch.branch,
                                brchcd=branch.brchcd,
                                tag="DEPO",
                                acctno=acctno,
                                c2cnt=1,
                                c2bal=ytdbal,
                            )
                        )
                    else:
                        rows.append(
                            SrsRecord(
                                staff=staff,
                                product=product,
                                ncore="N",
                                branch=branch.branch,
                                brchcd=branch.brchcd,
                                tag="DEPO",
                                acctno=acctno,
                                c3cnt=1,
                                c3bal=ytdbal,
                            )
                        )

    return rows


def read_elds(path: Path, branch_by_code: dict[str, Branch]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            aanum = line[0:13].strip()
            stafx1 = line[16:21].strip()
            stafx2 = line[25:30].strip()
            stafx3 = line[34:39].strip()
            product = line[50:68].strip()
            ytdbal = parse_sas_number(line[68:80])
            brchcd = aanum[:3]
            branch = branch_by_code.get(brchcd)
            if stafx1 == "*****" or branch is None:
                continue

            if "00001" <= stafx1 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx1),
                        product=product,
                        ncore="X",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c1cnt=1,
                        c1bal=ytdbal,
                    )
                )

            if "00001" <= stafx2 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx2),
                        product=product,
                        ncore="C",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c2cnt=1,
                        c2bal=ytdbal,
                    )
                )

            if "00001" <= stafx3 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx3),
                        product=product,
                        ncore="N",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c3cnt=1,
                        c3bal=ytdbal,
                    )
                )

    return rows


def attach_card_locations(
    cards: list[SrsRecord],
    hr_branch_by_staff: dict[int, HrBranch],
    hr_ho_by_staff: dict[int, HrHo],
) -> tuple[list[SrsRecord], list[SrsRecord], list[SrsRecord]]:
    branch_rows: list[SrsRecord] = []
    ho_rows: list[SrsRecord] = []
    unmatched: list[SrsRecord] = []

    for row in cards:
        hr_branch = hr_branch_by_staff.get(row.staff)
