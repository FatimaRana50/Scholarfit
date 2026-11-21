Prompt files are versioned with the code. Each file has a SYSTEM part and a USER part
separated by a line `### USER`. Placeholders look like <<name>>.
Change a prompt only using examples from the DEVELOPMENT split; record the git commit of
the prompt version used in every experiment run (run_experiment.py stores it).
