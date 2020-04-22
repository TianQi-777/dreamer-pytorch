import datetime
import os

from rlpyt.runners.minibatch_rl import MinibatchRlEval, MinibatchRl
from rlpyt.samplers.serial.sampler import SerialSampler
from rlpyt.utils.logging.context import logger_context

from dreamer.agents.atari_dreamer_agent import AtariDreamerAgent
from dreamer.algos.dreamer_algo import Dreamer
from dreamer.envs.modified_atari import AtariEnv, AtariTrajInfo
from dreamer.envs.wrapper import make_wapper
from dreamer.envs.one_hot import OneHotAction


def build_and_train(log_dir, game="pong", run_ID=0, cuda_idx=None, eval=False):
    env_kwargs = dict(
        game=game,
        frame_shape=(64, 64),  # dreamer uses this, default is 80, 104
        frame_skip=2,  # because dreamer action repeat = 2
        num_img_obs=1,  # get only the last observation. returns black and white frame
        repeat_action_probability=0.25  # Atari-v0 repeat action probability = 0.25
    )
    factory_method = make_wapper(AtariEnv, [OneHotAction], [{}])
    sampler = SerialSampler(
        EnvCls=factory_method,
        TrajInfoCls=AtariTrajInfo,  # default traj info + GameScore
        env_kwargs=env_kwargs,
        eval_env_kwargs=env_kwargs,
        batch_T=1,
        batch_B=1,
        max_decorrelation_steps=0,
        eval_n_envs=10,
        eval_max_steps=int(10e3),
        eval_max_trajectories=5,
    )
    algo = Dreamer(horizon=10, kl_scale=0.1)
    agent = AtariDreamerAgent(train_noise=0.4, eval_noise=0, expl_type="epsilon_greedy",
                              expl_min=0.1, expl_decay=2000/0.3)
    runner_cls = MinibatchRlEval if eval else MinibatchRl
    runner = runner_cls(
        algo=algo,
        agent=agent,
        sampler=sampler,
        n_steps=5e6,
        log_interval_steps=1e3,
        affinity=dict(cuda_idx=cuda_idx),
    )
    config = dict(game=game)
    name = "dreamer_" + game
    with logger_context(log_dir, run_ID, name, config, snapshot_mode="last", override_prefix=True,
                        use_summary_writer=True):
        runner.train()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--game', help='Atari game', default='pong')
    parser.add_argument('--run-ID', help='run identifier (logging)', type=int, default=0)
    parser.add_argument('--cuda-idx', help='gpu to use ', type=int, default=None)
    parser.add_argument('--eval', action='store_true')
    default_log_dir = os.path.join(
        os.path.dirname(__file__),
        'data',
        'local',
        datetime.datetime.now().strftime("%Y%m%d"))
    parser.add_argument('--log-dir', type=str, default=default_log_dir)
    args = parser.parse_args()
    log_dir = os.path.abspath(args.log_dir)
    i = args.run_ID
    while os.path.exists(os.path.join(log_dir, 'run_' + str(i))):
        print(f'run {i} already exists. ')
        i += 1
    print(f'Using run id = {i}')
    args.run_ID = i
    build_and_train(
        log_dir,
        game=args.game,
        run_ID=args.run_ID,
        cuda_idx=args.cuda_idx,
        eval=args.eval,
    )