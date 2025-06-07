import { MigrationInterface, QueryRunner } from 'typeorm';

export class SeedDefaultUser1735679350000 implements MigrationInterface {
  name = 'SeedDefaultUser1735679350000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Insert a default user for development/testing with mock-user-id
    await queryRunner.query(`
      INSERT INTO "users" ("id", "email", "password", "first_name", "last_name", "plan", "currentLeadQuotaUsed", "lastQuotaResetAt", "created_at", "updated_at") 
      VALUES (
        '00000000-0000-0000-0000-000000000001',
        'mock@example.com',
        'seedpassword', -- Placeholder password
        'Mock',
        'User',
        'free',
        0,
        NOW(),
        NOW(),
        NOW()
      ) 
      ON CONFLICT ("id") DO NOTHING;
    `);

    // Insert another user with starter plan for testing
    await queryRunner.query(`
      INSERT INTO "users" ("id", "email", "password", "first_name", "last_name", "plan", "currentLeadQuotaUsed", "lastQuotaResetAt", "created_at", "updated_at") 
      VALUES (
        '00000000-0000-0000-0000-000000000002',
        'starter@example.com',
        'seedpassword', -- Placeholder password
        'Starter',
        'User',
        'starter',
        5,
        NOW(),
        NOW(),
        NOW()
      ) 
      ON CONFLICT ("id") DO NOTHING;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Remove the seeded users
    await queryRunner.query(`DELETE FROM "users" WHERE "id" IN ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002');`);
  }
}
