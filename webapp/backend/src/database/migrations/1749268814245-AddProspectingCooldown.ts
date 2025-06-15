import { MigrationInterface, QueryRunner } from 'typeorm';

export class AddProspectingCooldown1749268814245 implements MigrationInterface {
  name = 'AddProspectingCooldown1749268814245';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add prospect cooldown tracking fields to users table
    await queryRunner.query(`
      ALTER TABLE "users" 
      ADD COLUMN "lastProspectCompletedAt" TIMESTAMP NULL,
      ADD COLUMN "prospectCooldownUntil" TIMESTAMP NULL
    `);

    // Create index for faster queries on cooldown fields
    await queryRunner.query(`
      CREATE INDEX "IDX_users_prospect_cooldown" ON "users" ("prospectCooldownUntil")
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Drop index first
    await queryRunner.query(`DROP INDEX "IDX_users_prospect_cooldown"`);
    
    // Remove cooldown columns
    await queryRunner.query(`
      ALTER TABLE "users" 
      DROP COLUMN "lastProspectCompletedAt",
      DROP COLUMN "prospectCooldownUntil"
    `);
  }
}