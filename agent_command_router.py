def handle_agent_command(agent, cmd: str):
    if cmd == "/approvals":
        return agent.list_approvals()
    if cmd.startswith("/approve "):
        return agent.approve_action(cmd.replace("/approve ", "").strip())
    if cmd.startswith("/reject "):
        return agent.reject_action(cmd.replace("/reject ", "").strip())
    if cmd == "/policy":
        return agent.autonomy_policy()
    if cmd == "/daily-brief":
        return agent.daily_brief()
    if cmd == "/send-daily-brief":
        return agent.send_daily_brief()
    if cmd == "/budget":
        return agent.budget_summary()
    if cmd.startswith("/budget-check "):
        return agent.budget_check(cmd.replace("/budget-check ", "").strip())
    if cmd == "/projects":
        return agent.list_projects()
    if cmd == "/multi-status":
        return agent.multi_project_status()
    if cmd == "/seed-multi-project":
        return agent.seed_multi_project_queue()
    if cmd == "/project-profile":
        return agent.project_profile_summary()
    if cmd.startswith("/project-profile "):
        return agent.project_profile_summary(cmd.replace("/project-profile ", "").strip())
    if cmd == "/tg-help":
        return agent.telegram_help()
    if cmd == "/tg-status":
        return agent.telegram_status()
    if cmd == "/tg-diagnose":
        return agent.telegram_diagnose()
    if cmd == "/tg-send-status":
        return agent.telegram_send_status()
    if cmd == "/secret-check":
        return agent.secret_health_check()
    if cmd.startswith("/tg-handle "):
        return agent.handle_telegram_command(cmd.replace("/tg-handle ", "").strip())
    if cmd == "/daemon-status":
        return agent.daemon_status()
    if cmd == "/daemon-once":
        return agent.daemon_once()
    if cmd.startswith("/daemon-once "):
        return agent.daemon_once(cmd.replace("/daemon-once ", "").strip())
    if cmd == "/daemon-send-digest":
        return agent.daemon_send_digest()
    if cmd.startswith("/route "):
        return agent.route_task(cmd.replace("/route ", "").strip())
    if cmd.startswith("/plan-task "):
        return agent.plan_routed_task(cmd.replace("/plan-task ", "").strip())
    if cmd.startswith("/propose-task "):
        return agent.propose_task(cmd.replace("/propose-task ", "").strip())
    if cmd == "/queue":
        return agent.list_queue()
    if cmd == "/queue-all":
        return agent.list_queue(include_done=True)
    if cmd.startswith("/queue "):
        return agent.list_queue(cmd.replace("/queue ", "").strip())
    if cmd == "/queue-next":
        return agent.queue_next()
    if cmd.startswith("/queue-next "):
        return agent.queue_next(cmd.replace("/queue-next ", "").strip())
    if cmd == "/queue-run-next":
        return agent.queue_run_next()
    if cmd.startswith("/queue-run-next "):
        return agent.queue_run_next(cmd.replace("/queue-run-next ", "").strip())
    if cmd.startswith("/queue-run "):
        return agent.queue_run_task(cmd.replace("/queue-run ", "").strip())
    if cmd.startswith("/queue-update "):
        parts = cmd.replace("/queue-update ", "").split(" ", 2)
        if len(parts) >= 2:
            note = parts[2] if len(parts) == 3 else ""
            return agent.queue_update(parts[0], parts[1], note)
        return "Uso: /queue-update <id> <status> [nota]"

    if cmd == "/audit":
        return agent.audit_project()
    if cmd == "/install":
        blocked = agent._guard_action("install", {"command": cmd, "summary": "Instalar dependencias"})
        if blocked:
            return blocked
        return agent.install_dependencies()
    if cmd == "/agents":
        return agent.subagents.list_agents()
    if cmd == "/memory":
        return f"? {agent.memory.get_context_prompt(agent.current_dir.name)}"

    if cmd.startswith("/delegate "):
        parts = cmd.replace("/delegate ", "").split(" ", 1)
        if len(parts) == 2:
            agent_name, task = parts
            return agent.subagents.delegate(task.strip('"'), agent_name)
        return 'Uso: /delegate [auditor|coder|debugger...] "tarea"'

    if cmd.startswith("/project "):
        return agent.switch_project(cmd.replace("/project ", "").strip())
    if cmd.startswith("/read "):
        return agent._read_file(cmd.replace("/read ", "").strip())
    if cmd.startswith("/ls"):
        return agent._list_dir()
    if cmd.startswith("/run "):
        blocked = agent._guard_action("shell", {"command": cmd, "shell": cmd.replace("/run ", "").strip()})
        if blocked:
            return blocked
        return agent._run_command(cmd.replace("/run ", "").strip())

    if cmd == "/init-business":
        return agent.init_business_project()
    if cmd == "/define-niche":
        return agent.define_niche()
    if cmd == "/create-mvp":
        return agent.create_mvp_product()
    if cmd == "/setup-store":
        return agent.setup_store()
    if cmd == "/generate-content":
        return agent.generate_content_batch()
    if cmd == "/dashboard":
        return agent.track_metrics()
    if cmd == "/add-task":
        return 'Uso: /add-task "tarea" alta/media/baja'
    if cmd.startswith("/add-task "):
        parts = cmd.replace("/add-task ", "").strip('"').split()
        if len(parts) >= 1:
            task = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]
            priority = parts[-1] if parts[-1] in ["alta", "media", "baja"] else "media"
            return agent.add_task(task, priority)
        return "Error en formato"
    if cmd == "/tasks":
        return agent.list_tasks()
    if cmd.startswith("/complete-task "):
        try:
            idx = int(cmd.replace("/complete-task ", ""))
            return agent.complete_task(idx)
        except Exception:
            return "? Usá: /complete-task <número>"

    if cmd == "/gumroad-publish":
        blocked = agent._guard_action("publish", {"command": cmd, "summary": "Publicar producto en Gumroad"})
        if blocked:
            return blocked
        return agent.publish_to_gumroad()
    if cmd == "/gumroad-sales":
        return agent.check_gumroad_sales()
    if cmd == "/gumroad-list":
        return agent.list_gumroad_products()

    if cmd == "/autonomous-start":
        blocked = agent._guard_action("autonomous_start", {"command": cmd, "summary": "Iniciar modo autonomo"})
        if blocked:
            return blocked
        return agent.autonomous_engine.start_autonomous_mode(interval_minutes=30)
    if cmd == "/autonomous-stop":
        return agent.autonomous_engine.stop_autonomous_mode()
    if cmd == "/autonomous-status":
        return agent.autonomous_engine.get_status()
    if cmd == "/autonomous-now":
        agent.autonomous_engine.run_cycle()
        return "? Ciclo autónomo ejecutado"

    return None
